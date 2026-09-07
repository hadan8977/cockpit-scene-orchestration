"""Paired, item-clustered analysis. All added quality checks are applied to every arm."""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
import run_eval as R
from safe_eval import read_rows, atomic

HERE=Path(__file__).resolve().parent

def language_ok(row):
    p=row["score"].get("parsed") or {}
    texts=[p.get(k) for k in ("understanding","say","clarify") if isinstance(p.get(k),str) and p[k].strip()]
    for text in texts:
        cjk=len(re.findall(r"[\u4e00-\u9fff]",text)); latin=len(re.findall(r"[A-Za-z]",text))
        if row["lang"]=="en" and (latin==0 or cjk>latin): return False
        if row["lang"]=="zh" and cjk==0: return False
    return True

def usable(row):
    return bool(not row["error"] and row["score"].get("pass") and row["score"].get("name_ok") and language_ok(row))

def stats(rows):
    good=[r for r in rows if not r["error"]]
    if not good: return {"n":len(rows),"errors":len(rows)}
    n=len(good)
    return {"n":len(rows),"errors":len(rows)-n,"task_pass":sum(r["score"]["pass"] for r in good)/n,
            "usable_pass":sum(usable(r) for r in good)/n,"name_ok":sum(bool(r["score"].get("name_ok")) for r in good)/n,
            "language_ok":sum(language_ok(r) for r in good)/n,
            "safety_violations":sum(any("安全违规" in v for v in r["score"]["violations"]) for r in good),
            "schema_valid":sum(r["score"].get("schema_valid",False) for r in good)/n,
            "strict_json_valid":sum(r["score"].get("strict_json_valid",False) for r in good)/n,
            "latency_p50":R.pct([r["latency"] for r in good],.5),"latency_p95":R.pct([r["latency"] for r in good],.95),
            "ttft_p50":R.pct([r["ttft"] for r in good if r.get("ttft") is not None],.5),
            "understanding_p50":R.pct([r["t_und"] for r in good if r.get("t_und") is not None],.5)}

def paired(a,b,metric=usable,iterations=3000):
    key=lambda r:(r["id"],r["lang"],r["rep"])
    aa={key(r):r for r in a if not r["error"]}; bb={key(r):r for r in b if not r["error"]}
    common=sorted(aa.keys() & bb.keys())
    groups=defaultdict(list)
    wins=losses=ties=0
    for k in common:
        delta=float(metric(bb[k]))-float(metric(aa[k]))
        groups[k[0]].append(delta)
        wins+=delta>0; losses+=delta<0; ties+=delta==0
    if not groups: return {"pairs":0}
    rng=random.Random(20260907); ids=sorted(groups); boot=[]
    for _ in range(iterations):
        sampled=[d for id in rng.choices(ids,k=len(ids)) for d in groups[id]]
        boot.append(sum(sampled)/len(sampled))
    return {"pairs":len(common),"clusters":len(groups),"b_wins":wins,"a_wins":losses,"ties":ties,
            "delta_b_minus_a":sum(sum(v) for v in groups.values())/len(common),
            "ci95_cluster_bootstrap":[R.pct(boot,.025),R.pct(boot,.975)]}

def analyze(run):
    path=HERE/"results"/"prompt-lab-v3"/run
    allrows=read_rows(path/"raw.jsonl")
    # Last completed response for each experimental unit; failed attempts remain in raw.
    latest={}
    for r in allrows:
        k=(r["variant"],r["id"],r["lang"],r["rep"])
        if k not in latest or not r["error"]: latest[k]=r
    allrows=list(latest.values())
    arms={v:[r for r in allrows if r["variant"]==v] for v in sorted({r["variant"] for r in allrows})}
    result={"run_id":run,"metric_note":"usable = original task pass AND required name AND reply language; identical checks for all arms; language check is lexical and needs qualitative review", "variants":{}}
    for v,rows in arms.items():
        result["variants"][v]={**stats(rows),"by_lang":{l:stats([r for r in rows if r["lang"]==l]) for l in ("zh","en")}}
    keys=list(arms)
    result["paired"]={a+" -> "+b:paired(arms[a],arms[b]) for i,a in enumerate(keys) for b in keys[i+1:]}
    zh=next((v for v in arms if v.endswith("_zh")),None)
    en=next((v for v in arms if v.endswith("_en")),None)
    if zh and en:
        split=[r for r in arms[zh] if r["lang"]=="zh"]+[r for r in arms[en] if r["lang"]=="en"]
        result["language_policies"]={"unified_zh":stats(arms[zh]),"unified_en":stats(arms[en]),"matched_split":stats(split)}
        result["language_pairs"]={l:paired([r for r in arms[zh] if r["lang"]==l],[r for r in arms[en] if r["lang"]==l]) for l in ("zh","en")}
    result["failures"]=[{"variant":r["variant"],"id":r["id"],"lang":r["lang"],"rep":r["rep"],"reason":r["score"]["fail_reason"],"name_ok":r["score"].get("name_ok"),"language_ok":language_ok(r)} for r in allrows if not usable(r)]
    atomic(path/"analysis.json",result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("failures","paired")},ensure_ascii=False,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("run");a=p.parse_args();analyze(a.run)
