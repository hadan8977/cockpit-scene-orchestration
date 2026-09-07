"""Fixed-quota sample selection for the holdout experience review. Quotas set before the first holdout judge call."""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import review as J
from study import HERE, rows, save, sha, encoded

# Category quotas fixed here, proportional to the holdout distribution, attack excluded because both
# arms return an empty proposal on those and an experience score carries no information.
QUOTAS = {"action": 7, "precise": 7, "vague": 5, "affect": 5, "clarify": 3, "robust": 3,
          "explicit": 4, "weak": 2, "memory": 2, "observe": 2}


def main(run="16_holdout", candidate="p26", baseline="v3_inline", name="holdout-p26-vs-v3"):
    records = rows(HERE / "results" / run / "raw.jsonl")
    index = {(r["id"], r["lang"], r["variant"]): r for r in records if r["rep"] == 0}
    groups = {}
    for r in records:
        groups.setdefault(r["cat"], set()).add(r["id"])
    randomizer = random.Random(2026090717)
    selected = []
    for cat, count in QUOTAS.items():
        ids = sorted(groups.get(cat, []))
        randomizer.shuffle(ids)
        selected += ids[:count]
    samples = []
    for case_id in selected:
        for lang in ("zh", "en"):
            a, b = index[case_id, lang, candidate], index[case_id, lang, baseline]

            def output(r):
                try:
                    return J.strict_json(r["raw_text"])
                except ValueError:
                    return {"invalid_response": r["raw_text"], "transport_error": r["error"]}
            for reverse in (False, True):
                samples.append({"sample_id": f"{case_id}-{lang}-{'BA' if reverse else 'AB'}", "id": case_id,
                                "locale": lang, "cat": a["cat"], "input": a["input"], "context": a["context"],
                                "A": output(b if reverse else a), "B": output(a if reverse else b),
                                "candidate_position": "B" if reverse else "A"})
    plan = {"name": name, "source_run": run, "candidate": candidate, "baseline": baseline, "ids": selected,
            "models": ["luna", "qwen"], "samples": len(samples), "calls": 2 * len(samples),
            "sample_sha256": sha(encoded(samples)),
            "selection": "Fixed category quotas set before the first holdout judge call; seed 2026090717; rep 0; both locales and both positions; attack excluded; no score-based filtering.",
            "report_rule": "All dimensions separately by judge, position and locale. Missing ratings are not imputed. Cluster by original case id. The holdout may not be used to tune this candidate after these calls."}
    save(HERE / "judge" / (name + "-samples.json"), samples)
    save(HERE / "judge" / (name + "-plan.json"), plan)
    print(json.dumps({"prepared": name, "items": len(selected), "pairs": len(samples) // 2, "calls": len(samples) * 2}))


if __name__ == "__main__":
    main(*sys.argv[1:])
