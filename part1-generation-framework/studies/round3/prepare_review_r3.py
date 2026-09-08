"""Round-three blind experience review sampling. Quotas fixed before the first judge call."""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import review as J
from study import HERE, rows, save, sha, encoded

# attack excluded: both arms return an empty proposal, an experience score carries no information there.
OUT_OF_SCOPE = set("A01 A05 A09 A14 C05 C09 D02 F12 N01 N05 N10 R3H001 R3H002 R3H003 R3H004 R3H005 R3H007 R3H008 R3H009 R3H022 R3H039 R3H046 R3H047 R3H048 R3H049 R3H050".split())

QUOTAS_40 = {"action": 6, "precise": 7, "vague": 4, "affect": 4, "weak": 4, "clarify": 3,
             "robust": 3, "explicit": 4, "memory": 3, "observe": 2}
QUOTAS_32 = {"action": 5, "precise": 6, "vague": 3, "affect": 3, "weak": 3, "clarify": 2,
             "robust": 2, "explicit": 3, "memory": 3, "observe": 2}

RUNS = ["r3_05_equal"]


def load(runs=None):
    index, groups = {}, {}
    for run in (runs or RUNS):
        src = HERE / "results" / run / "raw.jsonl"
        if not src.exists(): continue
        for r in rows(src):
            if r["rep"] != 0:
                continue
            if r["id"] in OUT_OF_SCOPE: continue
            index[r["id"], r["lang"], r["variant"]] = r
            groups.setdefault(r["cat"], set()).add(r["id"])
    return index, groups


def main(name, candidate, baseline, quota_key, seed, runs=None):
    runs = runs.split(",") if runs else RUNS
    index, groups = load(runs)
    if quota_key == "all":
        quotas = {c: len(ids) for c, ids in groups.items() if c != "attack"}
    else:
        quotas = {"40": QUOTAS_40, "32": QUOTAS_32}[quota_key]
    randomizer = random.Random(int(seed))
    selected = []
    for cat, count in quotas.items():
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
    plan = {"name": name, "source_runs": runs, "scoring_contract": "v4", "candidate": candidate,
            "baseline": baseline, "ids": selected, "models": ["luna", "qwen"], "samples": len(samples),
            "calls": 2 * len(samples), "sample_sha256": sha(encoded(samples)),
            "selection": f"Fixed category quotas registered in AMENDMENT-R3-01 before the first round-three judge call; seed {seed}; rep 0; both locales and both positions; attack excluded; no score-based filtering.",
            "report_rule": "All four dimensions reported separately, by judge and by position. Missing ratings are not imputed. Item-level cluster bootstrap for the confidence interval, Holm correction across dimensions."}
    save(HERE / "judge" / (name + "-samples.json"), samples)
    save(HERE / "judge" / (name + "-plan.json"), plan)
    print(json.dumps({"prepared": name, "items": len(selected), "pairs": len(samples) // 2, "calls": len(samples) * 2}))


if __name__ == "__main__":
    main(*sys.argv[1:])
