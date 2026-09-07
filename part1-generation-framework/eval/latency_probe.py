"""Paired cold-connection / pooled-connection test; identical prompt and model body.

Both arms fully consume the SSE response so the pooled arm can actually reuse TCP.
This is deployment transport evidence, not a claimed prompt-only latency gain.
"""
import argparse
import json
import random
import time
from pathlib import Path
import requests
import run_eval as R
from safe_eval import Budget, atomic, append, read_rows, campaign_lock, credentials, digest, summarize, strict_json, balance
HERE=Path(__file__).resolve().parent
ROOT=HERE/"results"/"prompt-lab-v3"
IDS=["A01","A04","B01","B03","C01","C05","E01","E03","E05","F01","G07","J01"]

def run(env,prompt):
    out=ROOT/"10_latency";out.mkdir(parents=True,exist_ok=True)
    key=credentials(env);system=(HERE/prompt).read_text(encoding="utf-8")
    items=[r for r in read_rows(HERE/"testset.jsonl") if r["id"] in IDS]
    jobs=[(i,l,rep,a) for rep in range(3) for i in items for l in ("zh","en") for a in ("cold","pooled")]
    random.Random(74122).shuffle(jobs)
    manifest={"expected":len(jobs),"repeat":3,"model":"deepseek-v4-flash","prompt":prompt,"prompt_sha256":digest(system.encode()),"items_sha256":digest(items),"code_sha256":digest(Path(__file__).read_bytes()),"scorer_sha256":digest((HERE/"run_eval.py").read_bytes()),"one_variable":"requests Session reuse; both arms drain body after DONE","temperature":0,"max_tokens":1000,"json_mode":True,"input_envelope":True,"concurrency":1}
    if (out/"manifest.json").exists() and json.loads((out/"manifest.json").read_text(encoding="utf-8"))!=manifest: raise RuntimeError("Manifest mismatch")
    atomic(out/"manifest.json",manifest)
    old=read_rows(out/"raw.jsonl");done={(r["id"],r["lang"],r["rep"],r["variant"]) for r in old if not r["error"]}
    R.apply_style("p3")
    cfg={"base_url":"https://api.deepseek.com","api_key":key,"model":"deepseek-v4-flash","temperature":0,"max_tokens":1000,"timeout":60,"thinking":"off","thinking_style":"deepseek","json_mode":True,"_budget_guarded":True}
    original_post=requests.post
    with campaign_lock(ROOT/"campaign.lock"),requests.Session() as session:
        budget=Budget(ROOT/"campaign.json",key,max_attempts=5000)
        pooled_calls=0
        for item,lang,rep,arm in jobs:
            if (item["id"],lang,rep,arm) in done: continue
            inp=item["input_en" if lang=="en" else "input"];ctx=item.get("context_en" if lang=="en" else "context") or ""
            user=json.dumps({"locale":lang,"context":ctx,"utterance":inp},ensure_ascii=False,separators=(",",":"))
            index=budget.start("10_latency",[item["id"],lang,rep,arm],system,user,1000)
            post=session.post if arm=="pooled" else original_post
            def draining_post(*args,**kwargs):
                response=post(*args,**kwargs)
                original_lines=response.iter_lines
                def lines(*a,**kw):
                    iterator=original_lines(*a,**kw)
                    for line in iterator:
                        if line in ("data: [DONE]",b"data: [DONE]"):
                            for _ in iterator: pass
                        yield line
                response.iter_lines=lines
                return response
            try:
                requests.post=draining_post
                start=time.perf_counter();result=R._call_model_once(cfg,system,user);elapsed=time.perf_counter()-start
            finally:
                requests.post=original_post
            budget.finish(index,result)
            obj=R.extract_json(result.get("text"));score=R.score_item(dict(item,_lang=lang),obj,"p3")
            try: strict_json(result.get("text") or "");score["strict_json_valid"]=True
            except (ValueError,TypeError): score["strict_json_valid"]=False;score["pass"]=False
            row={"id":item["id"],"cat":item["cat"],"lang":lang,"rep":rep,"variant":arm,"input":inp,"context":ctx,"raw_text":result.get("text"),"error":result.get("error"),"usage":result.get("usage"),"latency":elapsed,"ttft":result.get("ttft"),"t_und":result.get("t_und"),"score":score,"attempt_index":index,"pooled_first_request":arm=="pooled" and pooled_calls==0}
            if arm=="pooled":pooled_calls+=1
            append(out/"raw.jsonl",row);old.append(row)
            atomic(out/"summary.json",summarize(old,len(jobs),3))
            print(arm,item["id"],lang,"%.3fs / understanding %.3fs"%(elapsed,result.get("t_und") or 0),flush=True)
        budget.data["last_balance_cny"]=balance(key);atomic(budget.path,budget.data)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--env-file",required=True);p.add_argument("--prompt",required=True);a=p.parse_args();run(a.env_file,a.prompt)
