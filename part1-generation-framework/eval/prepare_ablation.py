"""Stratified diagnostic subset, fixed seed; not a new holdout test."""
import json
import random
import importlib
from pathlib import Path
import build_p10 as P9
HERE=Path(__file__).resolve().parent
COUNTS={"attack":8,"action":4,"precise":4,"vague":3,"affect":3,"robust":2,"weak":1,"memory":2,"observe":1,"clarify":2,"explicit":2}

def prepare(lang, version="p10", run_id="06_ablation", max_attempts=3500):
    builder=importlib.import_module("build_"+version)
    rows=[json.loads(x) for x in (HERE/"testset_core.jsonl").read_text(encoding="utf-8").splitlines() if x]
    rng=random.Random(60231); selected=[]
    for cat,n in COUNTS.items():
        pool=[r for r in rows if r["cat"]==cat]
        assert len(pool)>=n,(cat,n,len(pool))
        selected.extend(rng.sample(pool,n))
    selected.sort(key=lambda r:r["id"])
    assert len(selected)==32
    dataset=HERE/"experiments"/"ablation32.jsonl"
    content="".join(json.dumps(r,ensure_ascii=False)+"\n" for r in selected)
    if dataset.exists() and dataset.read_text(encoding="utf-8")!=content: raise RuntimeError("Subset changed")
    dataset.write_text(content,encoding="utf-8")
    variants=[{"name":"full","prompt":"prompts/%s_%s.md"%(version,lang)},
              {"name":"baseline_p3","prompt":"prompts/p3_grammar.generated.md"}]
    base=builder.build(lang)
    for block in ("safety","memory","brevity","examples"):
        text=builder.build(lang,remove=(block,))
        # The only difference is deletion of the named block, including its header.
        expected=base.replace("["+block+"]\n"+builder.blocks(lang)[block],"",1)
        assert text==expected and text!=base
        pp="prompts/%s_%s_without_%s.md"%(version,lang,block)
        (HERE/pp).write_text(text,encoding="utf-8")
        variants.append({"name":"without_"+block,"prompt":pp})
    plan={"run_id":"06_ablation","purpose":"Four single-block deletion ablations of p10; other bytes/config fixed. Safety remains partly encoded in effective dictionary and final check, so this tests incremental safety-block value, not removal of all defenses.","testset":"experiments/ablation32.jsonl","repeat":1,"temperature":0,"max_tokens":1000,"json_mode":True,"input_envelope":True,"concurrency":3,"seed":20260912,"campaign_max_attempts":3500,"variants":variants}
    plan.update(run_id=run_id,campaign_max_attempts=max_attempts)
    plan["purpose"]=plan["purpose"].replace("p10",version)
    (HERE/"experiments"/(run_id+".json")).write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Prepared %d items x 2 languages x 6 variants = 384 calls"%len(selected))

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--lang",choices=["zh","en"],required=True)
    ap.add_argument("--version",default="p10");ap.add_argument("--run-id",default="06_ablation");ap.add_argument("--max-attempts",type=int,default=3500)
    a=ap.parse_args();prepare(a.lang,a.version,a.run_id,a.max_attempts)
