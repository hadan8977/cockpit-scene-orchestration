"""Capability-only gold audit before any held-out model call."""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from study import HERE, rows, save, sha, encoded
sys.path.insert(0,str(HERE.parents[1]/"runtime"))
from core import Registry, _typed_value


def main():
    records=rows(HERE/"holdout-v2.jsonl");fixed=copy.deepcopy(records);changes=[]
    for item in fixed:
        for alt in item["alts"]:
            for entry in alt["conditions"].get("items",[]):
                if entry["primary"]=="主驾车门":
                    changes.append({"id":item["id"],"field":"condition.primary","before":"主驾车门","after":"左前门","reason":"Author used a non-registry display alias; current registry's driver door is 左前门"});entry["primary"]="左前门"
                if entry["primary"]=="车内PM2.5" and entry["value"]=="60":
                    changes.append({"id":item["id"],"field":"condition.value","before":"60","after":60,"reason":"Numeric gold matches parsed quantity; output still must carry μg/m³ and satisfy step"});entry["value"]=60
    names={c["zh"]:c for c in Registry().snapshot()["capabilities"]};errors=[]
    for item in fixed:
        for alt in item["alts"]:
            for kind in ("conditions","actions"):
                gold=alt[kind]
                for entry in gold.get("items",[])+gold.get("must_have",[])+gold.get("one_of",[]):
                    cap=names.get(entry["primary"])
                    if not cap or not cap.get("cond_values" if kind=="conditions" else "act_values"):errors.append([item["id"],kind,entry["primary"]]);continue
                    for value in entry.get("secondary_any",[]):
                        if not _typed_value(cap,kind,value):errors.append([item["id"],kind,entry["primary"],value])
                    if kind=="conditions":
                        value=entry.get("value")
                        if isinstance(value,str) and not _typed_value(cap,kind,value):errors.append([item["id"],kind,entry["primary"],value])
    if errors:raise ValueError(errors)
    output=HERE/"holdout-v2.1.jsonl"
    if output.exists():raise RuntimeError("Preflight revision already written")
    output.write_bytes(b"".join(encoded(x)+b"\n" for x in fixed))
    save(HERE/"holdout-v2.1-manifest.json",{"parent_sha256":sha((HERE/"holdout-v2.jsonl").read_bytes()),"sha256":sha(output.read_bytes()),"cases":80,"changes":changes,"model_calls_before_correction":0,"reason":"Offline registry gold audit; original v2 kept. Both versions unqueried. This is one confirmation set, not two independent holdouts.","errors":errors})
    print(json.dumps({"gold_preflight":"pass","corrected_entries":len(changes)}))


if __name__=="__main__":main()
