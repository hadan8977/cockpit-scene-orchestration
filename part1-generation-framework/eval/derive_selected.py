"""Export a selected policy's EXISTING responses; makes zero API calls.

This is a transparent derived dataset, not an independent post-selection run.
"""
import argparse
import json
from pathlib import Path
from safe_eval import read_rows, atomic, digest, summarize
HERE=Path(__file__).resolve().parent
ROOT=HERE/"results"/"prompt-lab-v3"

def derive(source,strategy,out_name):
    src=ROOT/source;out=ROOT/out_name
    summary=json.loads((src/"summary.json").read_text(encoding="utf-8"))
    if summary["status"]!="complete":raise RuntimeError("Source study must be complete before selection")
    rows=read_rows(src/"raw.jsonl")
    latest={}
    for r in rows:
        if not r["error"]:latest[r["variant"],r["id"],r["lang"],r["rep"]]=r
    choose=lambda r: r["variant"].endswith("_"+(r["lang"] if strategy=="matched_split" else strategy.rsplit("_",1)[1]))
    selected=[r for r in latest.values() if choose(r)]
    keys={(r["id"],r["lang"],r["rep"]) for r in selected}
    if len(keys)!=len(selected) or len(selected)!=804:raise RuntimeError("Expected exactly one response per 134 x 2 x 3 unit")
    source_manifest=json.loads((src/"manifest.json").read_text(encoding="utf-8"))
    manifest={"kind":"derived_selection","new_api_calls":0,"independent_post_selection_regression":False,
              "source_run":source,"source_raw_sha256":digest((src/"raw.jsonl").read_bytes()),
              "source_manifest_sha256":digest((src/"manifest.json").read_bytes()),
              "strategy":strategy,"expected":804,"repeat":3,
              "source_prompt_sha256":source_manifest["prompt_sha256"],
              "source_selected_rows_sha256":digest(selected),
              "note":"Only metadata is added; input, raw_text, timings, usage and scores are copied verbatim. Do not count these rows as additional calls."}
    derived=[dict(r,source_run=source,source_variant=r["variant"],variant="final") for r in selected]
    if (out/"raw.jsonl").exists() and read_rows(out/"raw.jsonl")!=derived:raise RuntimeError("Existing derived selection differs")
    out.mkdir(parents=True,exist_ok=True)
    (out/"raw.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in derived),encoding="utf-8",newline="\n")
    atomic(out/"manifest.json",manifest)
    result=summarize(derived,804,3);result.update(kind="derived_selection",new_api_calls=0,source_run=source)
    atomic(out/"summary.json",result)
    print("Derived 804 existing responses; zero new API calls")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--strategy",choices=["unified_zh","unified_en","matched_split"],required=True);p.add_argument("--out",default="07b_final_selected");a=p.parse_args();derive(a.source,a.strategy,a.out)
