"""Frozen-result audit: no paid calls, no gold changes, no post-validator rescoring."""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import run_eval as R
from safe_eval import atomic, read_rows
from analyze_experiments import stats, usable, paired

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results" / "prompt-lab-v3"

def usage_stats(rows):
    usages=[r["usage"] for r in rows if not r["error"] and r.get("usage")]
    n=len(usages);total=sum(u.get("prompt_tokens",0) for u in usages)
    return {"n_with_usage":n,"input_mean":total/n if n else None,
            "output_mean":sum(u.get("completion_tokens",0) for u in usages)/n if n else None,
            "input_cache_hit_fraction":sum(u.get("prompt_cache_hit_tokens",0) for u in usages)/total if total else None}

def signature(row, canonical=False):
    p = row["score"].get("parsed") or {}
    conditions = p.get("conditions", [])
    actions = p.get("actions", [])
    if canonical:
        # AND/OR condition order is commutative. Preserve ALL action ordering.
        conditions = sorted(conditions, key=lambda x: json.dumps(x, ensure_ascii=False))
    return json.dumps([p.get("intent"), p.get("logic"), conditions, actions], ensure_ascii=False, sort_keys=True)

def consistency(rows, repeat=3):
    groups = defaultdict(list)
    for r in rows:
        groups[r["id"], r["lang"]].append(r)
    complete = [g for g in groups.values() if len(g)==repeat and len({r["rep"] for r in g})==repeat and all(not r["error"] for r in g)]
    n = len(groups)
    return {"groups": n, "complete_groups": len(complete),
            "exact": sum(len({signature(r) for r in g})==1 for g in complete)/n if n else None,
            "condition_order_invariant": sum(len({signature(r, True) for r in g})==1 for g in complete)/n if n else None,
            "all_three_usable": sum(all(usable(r) for r in g) for g in complete)/n if n else None}

def audit(run):
    path = ROOT / run
    original = read_rows(path / "raw.jsonl")
    latest = {}
    for r in original:
        key = r["variant"], r["id"], r["lang"], r["rep"]
        if key not in latest or not r["error"]:
            latest[key] = r
    rows = list(latest.values())
    good = [r for r in rows if not r["error"]]
    nonempty_understanding = [r["t_und"] for r in good if r.get("t_und") is not None and (r["score"].get("parsed") or {}).get("understanding", "").strip()]
    named=[r for r in good if (r["score"].get("parsed") or {}).get("name")]
    def name_lang_ok(r):
        name=r["score"]["parsed"]["name"]
        return bool(re.search(r"[\u4e00-\u9fff]" if r["lang"]=="zh" else r"[A-Za-z]",name))
    attack = [r for r in good if r["cat"]=="attack"]
    violated = lambda r: bool((r["score"].get("parsed") or {}).get("actions") or (r["score"].get("parsed") or {}).get("memory"))
    result = {"run_id": run, "raw_attempt_rows": len(original), "experimental_units": len(rows),
              "usage":usage_stats(rows),
              "overall": stats(rows), "by_cat": {c: stats([r for r in rows if r["cat"]==c]) for c in sorted({r["cat"] for r in rows})},
              "nonempty_understanding": {"n":len(nonempty_understanding),"p50":R.pct(nonempty_understanding,.5),"p95":R.pct(nonempty_understanding,.95)},
              "name_language_diagnostic":{"named_responses":len(named),"contains_locale_script":sum(name_lang_ok(r) for r in named),"failures":[{"id":r["id"],"lang":r["lang"],"rep":r["rep"],"name":r["score"]["parsed"]["name"]} for r in named if not name_lang_ok(r)],"note":"Additional diagnostic only; original usable metric unchanged. Checks script presence, not fluency."},
              "by_lang": {l: stats([r for r in rows if r["lang"]==l]) for l in ("zh","en")},
              "consistency_note": "All complete triples; exact intent/logic/conditions/actions. Secondary metric ignores condition order only; action order retained. Missing triples count inconsistent. No semantic-alternate collapsing.",
              "rule_consistency": consistency([r for r in rows if r["cat"] in ("precise", "observe")]),
              "all_consistency": consistency(rows),
              "attack": {"responses": len(attack), "unique_items": len({r["id"] for r in attack}),
                         "action_or_memory": sum(violated(r) for r in attack), "task_failures": sum(not usable(r) for r in attack)},
              "failure_counts_by_id": dict(Counter(r["id"] for r in rows if not usable(r))),
              "failures": [{"id": r["id"], "lang": r["lang"], "rep": r["rep"], "reason": r["score"]["fail_reason"], "violations":r["score"]["violations"]} for r in rows if not usable(r)]}
    result["language_gap_abs_pp"] = 100*abs(result["by_lang"]["zh"]["usable_pass"]-result["by_lang"]["en"]["usable_pass"])
    atomic(path / "audit.json", result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("failures", "by_cat", "by_lang")},ensure_ascii=False,indent=2))

def latency():
    path=ROOT/"10_latency";rows=read_rows(path/"raw.jsonl")
    cold=[r for r in rows if r["variant"]=="cold"]
    pooled=[r for r in rows if r["variant"]=="pooled"]
    result={"cold":stats(cold),"pooled":stats(pooled),"negative_delta_is_faster":True,
            "usage":{"cold":usage_stats(cold),"pooled":usage_stats(pooled)},
            "total_mean_paired":paired(cold,pooled,lambda r:r["latency"]),
            "understanding_mean_paired":paired(cold,pooled,lambda r:r["t_und"]),
            "note":"Serial same-prompt transport experiment; both arms drain SSE. Pooled includes first cold request. Cannot substitute these timings for concurrent full-regression timings."}
    atomic(path/"transport-analysis.json",result);print(json.dumps(result,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("run");a=p.parse_args()
    if a.run=="10_latency":latency()
    else:audit(a.run)
