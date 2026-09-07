"""Register the frozen-candidate regression and holdout plans. Run only after the candidate is fixed."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parents[1] / "eval"


def sha(d): return hashlib.sha256(d).hexdigest()


def ids_from(path):
    return [json.loads(l)["id"] for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


ap = argparse.ArgumentParser()
ap.add_argument("candidate")
a = ap.parse_args()
cand = f"prompts/{a.candidate}_zh.md"
assert (HERE / cand).exists(), cand

arms = {a.candidate: cand, "v3_inline": "prompts/v3_inline.md", "v0_contract": "prompts/v0_contract.md"}
dev = ids_from(EVAL / "testset.jsonl")
hold = ids_from(HERE / "holdout-v2.1.jsonl")

for run_id, ids, seed, source in (("15_full_regression", dev, 150015, "eval/testset.jsonl"),
                                  ("16_holdout", hold, 160016, "holdout-v2.1.jsonl")):
    plan = {"run_id": run_id, "repeat": 1, "seed": seed, "ids": ids, "variants": arms}
    (HERE / f"plans/{run_id}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"plans/{run_id}.json  题源 {source}  {len(ids)} 题 x 中英 x {len(arms)} 臂 = {len(ids)*2*len(arms)} 次")

record = {"candidate": a.candidate, "frozen_at_registration": True,
          "prompt_sha256": {k: sha((HERE / v).read_bytes().replace(b"\r\n", b"\n")) for k, v in arms.items()},
          "dataset_sha256": {"development": sha((EVAL / "testset.jsonl").read_bytes().replace(b"\r\n", b"\n")),
                             "holdout": sha((HERE / "holdout-v2.1.jsonl").read_bytes().replace(b"\r\n", b"\n"))},
          "capabilities_sha256": sha((EVAL / "capabilities.json").read_bytes().replace(b"\r\n", b"\n")),
          "rule": "Holdout may not be used to tune this candidate after its first call."}
(HERE / "final-candidate-freeze.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("\n冻结记录 final-candidate-freeze.json 已写入")
