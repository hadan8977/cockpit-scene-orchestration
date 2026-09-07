"""Frozen sample selection and reporting for position-balanced quality A/B."""
import argparse
import gzip
import json
import random
import statistics
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review as J
from study import HERE, rows, save, sha, encoded


def prepare(run,candidate,baseline,name):
    records=rows(HERE/"results"/run/"raw.jsonl")
    index={(r["id"],r["lang"],r["variant"]):r for r in records if r["rep"]==0}
    groups={}
    for r in records:
        groups.setdefault(r["cat"],set()).add(r["id"])
    randomizer=random.Random(2026090716)
    selected=[]
    for cat,count in {"affect":4,"vague":4,"explicit":3,"weak":2,"action":2,"precise":1}.items():
        ids=sorted(groups[cat]);randomizer.shuffle(ids);selected+=ids[:count]
    samples=[]
    for case_id in selected:
        for lang in ("zh","en"):
            a=index[case_id,lang,candidate];b=index[case_id,lang,baseline]
            # Invalid JSON is shown as the actual response, never repaired.
            def output(r):
                try:return J.strict_json(r["raw_text"])
                except ValueError:return {"invalid_response":r["raw_text"],"transport_error":r["error"]}
            for reverse in (False,True):
                samples.append({"sample_id":f"{case_id}-{lang}-{'BA' if reverse else 'AB'}","id":case_id,"locale":lang,"cat":a["cat"],"input":a["input"],"context":a["context"],"A":output(b if reverse else a),"B":output(a if reverse else b),"candidate_position":"B" if reverse else "A"})
    plan={"name":name,"source_run":run,"candidate":candidate,"baseline":baseline,"ids":selected,"models":["luna","qwen"],"samples":len(samples),"calls":2*len(samples),"sample_sha256":sha(encoded(samples)),"selection":"Fixed category quotas; seed 2026090716; rep 0; both locales and both positions. No score-based filtering.","report_rule":"Report all dimensions separately by judge, position and locale. Missing ratings are not imputed; incomplete coverage prevents confirmed superiority. Cluster by original case id."}
    save(HERE/"judge"/(name+"-samples.json"),samples);save(HERE/"judge"/(name+"-plan.json"),plan)
    print(json.dumps({"prepared":name,"pairs":len(samples)//2,"calls":len(samples)*2}))


def summarize(name):
    plan=json.loads((HERE/"judge"/(name+"-plan.json")).read_text(encoding="utf-8"))
    samples=json.loads((HERE/"judge"/(name+"-samples.json")).read_text(encoding="utf-8"))
    lookup={s["sample_id"]:s for s in samples};records=rows(HERE/"judge"/name/"raw.jsonl");report={"plan":plan,"judges":{}}
    for model in plan["models"]:
        subset=[r for r in records if r["model"]==model];valid=[r for r in subset if r["rating"]]
        dimensions={}
        for dim in J.DIMS:
            cand=[];base=[];cluster={}
            for r in valid:
                s=lookup[r["sample_id"]];pos=s["candidate_position"];other="B" if pos=="A" else "A"
                x,y=r["rating"][pos][dim],r["rating"][other][dim]
                cand.append(x);base.append(y);cluster.setdefault(s["id"],[]).append(x-y)
            means=[statistics.mean(v) for v in cluster.values()];rng=random.Random(701)
            boot=sorted(statistics.mean(rng.choices(means,k=len(means))) for _ in range(5000)) if means else [0]*5000
            dimensions[dim]={"candidate":statistics.mean(cand) if cand else None,"baseline":statistics.mean(base) if base else None,"delta":statistics.mean([a-b for a,b in zip(cand,base)]) if cand else None,"cluster_ci95":[boot[125],boot[4874]],"positive_cluster_ci":boot[125]>0}
        report["judges"][model]={"expected":len(samples),"completed":len(subset),"valid":len(valid),"invalid_sample_ids":[r["sample_id"] for r in subset if not r["rating"]],"dimensions":dimensions,"all_dimensions_higher_descriptively":all((d["delta"] or 0)>0 for d in dimensions.values()),"confirmation_eligible":len(valid)==len(samples)}
    save(HERE/"judge"/name/"summary.json",report);print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run","summarize"]);ap.add_argument("name");ap.add_argument("--source-run",default="02_refinement");ap.add_argument("--candidate",default="p16");ap.add_argument("--baseline",default="v3_protocol");ap.add_argument("--env-file")
    a=ap.parse_args()
    if a.action=="prepare":prepare(a.source_run,a.candidate,a.baseline,a.name)
    elif a.action=="run":
        samples=json.loads((HERE/"judge"/(a.name+"-samples.json")).read_text(encoding="utf-8"));plan=json.loads((HERE/"judge"/(a.name+"-plan.json")).read_text(encoding="utf-8"))
        J.run_review(a.name,samples,plan["models"],a.env_file);summarize(a.name)
    else:summarize(a.name)
