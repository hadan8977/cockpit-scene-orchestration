"""Bounded round-two model runner. Frozen round-one source is imported, not edited."""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import random
import re
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
EVAL = HERE.parents[1] / "eval"
sys.path.insert(0, str(EVAL))
import run_eval as R
from safe_eval import strict_json

LOCK = threading.RLock()
LOCAL = threading.local()


def now(): return datetime.now(timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b"\n")
    for attempt in range(10):
        try: temp.replace(path); return
        except PermissionError:
            if attempt == 9: raise
            time.sleep(.05)


def append(path, value):
    with LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as f:
            f.write(encoded(value) + b"\n")
            f.flush()
            os.fsync(f.fileno())


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x] if path.exists() else []


def keys(path):
    result = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        k, sep, v = line.partition("=")
        if sep and k.strip() in ("DEEPSEEK_API_KEY", "DEEPSEEK_OFFICIAL_API_KEY", "OPENROUTER_API_KEY"):
            result[k.strip()] = v.strip().strip('"').strip("'")
    if "DEEPSEEK_OFFICIAL_API_KEY" in result: result["DEEPSEEK_API_KEY"] = result["DEEPSEEK_OFFICIAL_API_KEY"]
    return result


def session():
    if not hasattr(LOCAL, "http"):
        LOCAL.http = requests.Session()
        LOCAL.http.mount("https://", requests.adapters.HTTPAdapter(max_retries=0, pool_connections=2, pool_maxsize=2))
    return LOCAL.http


class Budget:
    def __init__(self, credential):
        self.keys = credential
        self.path = HERE / "private-ledger.json"
        if self.path.exists(): self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            b = self.balance()
            self.data = {"created": now(), "initial_cny": b, "last_cny": b, "ds_floor_cny": max(3, b-10), "ds_max_calls": 20000, "or_max_usd": 15.0, "or_max_calls": 8000, "attempts": []}
            save(self.path, self.data)

    def balance(self):
        r = requests.get("https://api.deepseek.com/user/balance", headers={"Authorization": "Bearer " + self.keys["DEEPSEEK_API_KEY"]}, timeout=20, allow_redirects=False)
        if r.status_code != 200: raise RuntimeError("Balance unavailable: HTTP " + str(r.status_code))
        return next(float(x["total_balance"]) for x in r.json()["balance_infos"] if x["currency"] == "CNY")

    def reserve(self, provider, job, prompt, max_tokens, prices=None):
        with LOCK:
            attempts = [a for a in self.data["attempts"] if a["provider"] == provider]
            cap = self.data["ds_max_calls" if provider == "deepseek" else "or_max_calls"]
            if len(attempts) >= cap: raise RuntimeError("STOP: call cap")
            if provider == "deepseek":
                b = self.balance()
                self.data["last_cny"] = b
                upper = (len(prompt.encode())*3 + max_tokens*9 + 384)/1e6
                pending = sum(a["upper"] for a in attempts if a["status"] == "reserved")
                if b-upper-pending < self.data["ds_floor_cny"]: raise RuntimeError("STOP: DeepSeek reserve/spend cap")
            else:
                upper = len(prompt.encode())*prices[0] + max_tokens*prices[1]
                cost = sum(a.get("charged", a["upper"]) for a in attempts)
                if cost + upper > self.data["or_max_usd"]: raise RuntimeError("STOP: judge spend cap")
            index = len(self.data["attempts"])
            self.data["attempts"].append({"index": index, "provider": provider, "job": job, "upper": upper, "status": "reserved", "at": now()})
            save(self.path, self.data)
            return index

    def finish(self, index, result):
        with LOCK:
            item = self.data["attempts"][index]
            item.update(status="completed", error=result.get("error"), usage=result.get("usage"))
            if isinstance((result.get("usage") or {}).get("cost"), (int, float)):
                item["charged"] = result["usage"]["cost"]
            save(self.path, self.data)


def generate(key, prompt, user, response_format=None):
    body = {"model": "deepseek-v4-flash", "messages": [{"role":"system","content":prompt},{"role":"user","content":user}], "temperature":0, "max_tokens":1000, "thinking":{"type":"disabled"}, "response_format":response_format or {"type":"json_object"}, "stream":True, "stream_options":{"include_usage":True}}
    start = time.perf_counter()
    result = {"raw_text":"", "ttft":None, "t_und":None, "latency":None, "usage":None, "error":None, "finish_reason":None}
    try:
        with session().post("https://api.deepseek.com/chat/completions", headers={"Authorization":"Bearer "+key}, json=body, stream=True, timeout=(15,45), allow_redirects=False) as response:
            if response.status_code != 200:
                result["error"] = "HTTP " + str(response.status_code)
                # Provider error body is bounded; never includes request headers.
                result["provider_error"] = response.text[:1000]
                return result
            for line in response.iter_lines(chunk_size=1, decode_unicode=False):
                if not line.startswith(b"data:"): continue
                data = line[5:].strip()
                if data == b"[DONE]": break
                event = json.loads(data)
                if event.get("usage"): result["usage"] = event["usage"]
                for choice in event.get("choices", []):
                    if choice.get("finish_reason"): result["finish_reason"] = choice["finish_reason"]
                    text = choice.get("delta", {}).get("content") or ""
                    if text and result["ttft"] is None: result["ttft"] = time.perf_counter()-start
                    result["raw_text"] += text
                    if result["t_und"] is None:
                        match = re.search(r'"understanding"\s*:\s*',result["raw_text"])
                        if match:
                            try:
                                value, _ = json.JSONDecoder().raw_decode(result["raw_text"][match.end():])
                                if isinstance(value,str): result["t_und"] = time.perf_counter()-start
                            except ValueError: pass
            if result["finish_reason"] not in ("stop",): result["error"] = "Incomplete completion: " + str(result["finish_reason"])
    except requests.RequestException as e: result["error"] = type(e).__name__
    except (ValueError, KeyError) as e: result["error"] = "Stream " + type(e).__name__
    finally: result["latency"] = time.perf_counter()-start
    return result


def score(item, lang, response):
    obj = None
    try: obj = strict_json(response["raw_text"])
    except (ValueError, TypeError): pass
    try: result = R.score_item(dict(item, _lang=lang), obj, "p3")
    except (ValueError, TypeError, KeyError, AttributeError): result = {"pass":False,"schema_valid":False,"violations":["Malformed structured response"],"name_ok":False,"intent_ok":False}
    result["strict_json_valid"] = isinstance(obj,dict)
    explanation = " ".join(str(obj.get(k) or "") for k in ("understanding","say","clarify")) if isinstance(obj,dict) else ""
    result["language_ok"] = not bool(re.search(r"[\u3400-\u9fff]", explanation)) if lang=="en" else True
    result["usable"] = bool(result.get("pass") and result.get("name_ok") and result["strict_json_valid"] and result["language_ok"] and not response["error"])
    return result


def summarize(records):
    answer = {}
    for variant in sorted({r["variant"] for r in records}):
        subset = [r for r in records if r["variant"]==variant]
        rate = lambda metric: sum(bool(r["score"].get(metric)) and not r["error"] for r in subset)/len(subset)
        valid = [r for r in subset if not r["error"]]
        answer[variant] = {"n":len(subset),"errors":len(subset)-len(valid),"usable":rate("usable"),"task_pass":rate("pass"),"schema":rate("schema_valid"),"intent":rate("intent_ok"),"name":rate("name_ok"),"language":rate("language_ok"),"safety":sum(any("安全违规" in v for v in r["score"].get("violations",[])) for r in subset),"p50":R.pct([r["latency"] for r in valid],.5),"p95":R.pct([r["latency"] for r in valid],.95),"understanding_p50":R.pct([r["t_und"] for r in valid if r["t_und"] is not None],.5),"by_cat":{cat:sum(r["score"]["usable"] for r in subset if r["cat"]==cat)/sum(r["cat"]==cat for r in subset) for cat in sorted({r["cat"] for r in subset})}}
    return answer


def run(plan_name, env, max_new=0):
    plan = json.loads((HERE/plan_name).read_text(encoding="utf-8"))
    credential = keys(env)
    R.apply_style("p3")
    prompts = {k:(HERE/v).read_text(encoding="utf-8") for k,v in plan["variants"].items()}
    items = rows(EVAL/"testset.jsonl") if "testset" not in plan else rows(HERE/plan["testset"])
    if plan.get("ids"): items = [x for x in items if x["id"] in plan["ids"]]
    jobs = []
    for rep in range(plan["repeat"]):
        block = [(item,lang,rep,v) for item in items for lang in plan.get("languages",["zh","en"]) for v in prompts]
        random.Random(plan["seed"]+rep).shuffle(block)
        jobs += block
    out = HERE/"results"/plan["run_id"]
    manifest = {"plan":plan,"created_before_first_call":True,"expected":len(jobs),"prompt_hashes":{k:sha(v.encode()) for k,v in prompts.items()},"dataset_hash":sha(encoded(items)),"source_hashes":{str(p.relative_to(HERE.parents[1])):sha(p.read_bytes().replace(b"\r\n",b"\n")) for p in [Path(__file__),EVAL/"run_eval.py",EVAL/"output_contract.py",EVAL/"schema.json",EVAL/"capabilities.json"]},"transport":"thread-local persistent Session; concurrency from SCENE_CONCURRENCY (default 16); no HTTP retries","model":"deepseek-v4-flash","parameters":{"temperature":0,"thinking":"disabled","json_mode":True,"max_tokens":1000}}
    if (out/"manifest.json").exists() and json.loads((out/"manifest.json").read_text(encoding="utf-8"))!=manifest: raise RuntimeError("Manifest mismatch; new run id required")
    save(out/"manifest.json",manifest)
    records = rows(out/"raw.jsonl")
    completed = {(x["id"],x["lang"],x["rep"],x["variant"]) for x in records}
    jobs = [job for job in jobs if (job[0]["id"],*job[1:]) not in completed]
    if max_new: jobs=jobs[:max_new]
    budget = Budget(credential)
    def work(job):
        item,lang,rep,variant=job
        context=item.get("context_en" if lang=="en" else "context") or ""
        utterance=item["input_en" if lang=="en" else "input"]
        user=json.dumps({"locale":lang,"context":context,"utterance":utterance},ensure_ascii=False,separators=(",",":"))
        index=budget.reserve("deepseek",[plan["run_id"],item["id"],lang,rep,variant],prompts[variant]+user,1000)
        response=generate(credential["DEEPSEEK_API_KEY"],prompts[variant],user)
        budget.finish(index,response)
        record={"id":item["id"],"lang":lang,"cat":item["cat"],"rep":rep,"variant":variant,"input":utterance,"context":context,"at":now(),"attempt":index,**response,"score":score(item,lang,response)}
        append(out/"raw.jsonl",record)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('SCENE_CONCURRENCY','16'))) as pool:
        for record in pool.map(work,jobs):
            records.append(record)
            if len(records)%32==0:
                save(out/"summary.json",summarize(records))
                print(json.dumps({"run":plan["run_id"],"completed":len(records),"expected":manifest["expected"]}),flush=True)
    save(out/"summary.json",summarize(records))
    data=(out/"raw.jsonl").read_bytes()
    packed=gzip.compress(data,mtime=0)
    (out/"raw.jsonl.gz").write_bytes(packed)
    save(out/"archive.json",{"raw_sha256":sha(data),"gzip_sha256":sha(packed),"rows":len(records)})
    print(json.dumps(summarize(records)),flush=True)


if __name__ == "__main__":
    ap=argparse.ArgumentParser();ap.add_argument("plan");ap.add_argument("--env-file",required=True);ap.add_argument("--max-new",type=int,default=0)
    args=ap.parse_args();run(args.plan,args.env_file,args.max_new)
