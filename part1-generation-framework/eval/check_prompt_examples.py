"""Offline schema check of literal JSON exemplars; no model calls."""
import json
import argparse
import importlib
import run_eval as R
ap=argparse.ArgumentParser();ap.add_argument("--version",default="p11");args=ap.parse_args()
builder=importlib.import_module("build_"+args.version)
R.apply_style("p3")
failures=0
for lang in ("zh", "en"):
    outputs = [json.loads(x[len("OUTPUT: "):]) for x in builder.blocks(lang)["examples"].splitlines() if x.startswith("OUTPUT: ")]
    errors=[{"index":i,"errors":R.parse_output(o)["schema_errors"]} for i,o in enumerate(outputs) if R.parse_output(o)["schema_errors"]]
    failures+=len(errors)
    print(json.dumps({"version":args.version,"lang":lang,"examples":len(outputs),"failures":errors},ensure_ascii=True))
assert builder.blocks("en")["examples"]==builder.blocks("zh")["examples"], "Language arms must have identical exemplars"
raise SystemExit(bool(failures))
