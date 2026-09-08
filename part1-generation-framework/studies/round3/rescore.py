"""Offline re-scoring of a stored run under a given contract. No API calls."""
import json, os, sys
os.environ.setdefault("SCENE_CONTRACT", "v4")
from pathlib import Path
import study as S
S.R.apply_style("p3")
S.R.apply_style("p3")

run = sys.argv[1]
src = Path(f"results/{run}/raw.jsonl")
items = {i["id"]: i for i in S.rows(S.EVAL / "testset.jsonl")}
extra = Path("holdout-r3.jsonl")
if extra.exists():
    for i in S.rows(extra): items.setdefault(i["id"], i)
out = []
for line in src.read_text(encoding="utf-8").splitlines():
    if not line.strip(): continue
    r = json.loads(line)
    resp = {k: r[k] for k in ("raw_text", "error", "finish_reason", "usage", "latency", "ttft", "t_und") if k in r}
    r["score"] = S.score(items[r["id"]], r["lang"], resp)
    out.append(r)
dst = Path(f"results/{run}/raw.v4.jsonl")
dst.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
print("rescored", len(out), "->", dst, "| contract:", os.environ["SCENE_CONTRACT"])
