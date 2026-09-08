"""Mechanically strip capability values the round-three table no longer authorises.

Only removals, no re-authoring: a value that cannot be produced cannot be required, permitted or forbidden.
Items whose gold becomes unsatisfiable are reported, not silently rewritten.
"""
import json, os, sys
from pathlib import Path
os.environ["SCENE_CAPS"] = "r3"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
import contract_limits as CL
vocab = json.loads((ROOT / "eval" / CL.VOCAB_FILE).read_text(encoding="utf-8"))
ACT = vocab["actions"]

def allowed(primary, value):
    spec = ACT.get(primary)
    if spec is None: return False
    if isinstance(spec, dict): return True          # range values are checked by the scorer
    return value in spec

SLOTS = ("items", "must_have", "one_of", "must_not", "acceptable")

def fix(path):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    changed, broken = [], []
    for r in rows:
        touched = False
        for ai, a in enumerate(r["alts"]):
            act = a["actions"]
            for slot in SLOTS:
                items = act.get(slot)
                if not items: continue
                kept = []
                for it in items:
                    if it["primary"] not in ACT:
                        touched = True; continue                      # capability gone entirely
                    vals = it.get("secondary_any")
                    if vals is None:
                        kept.append(it); continue
                    ok = [v for v in vals if allowed(it["primary"], v)]
                    if not ok:
                        touched = True; continue                      # every value gone
                    if len(ok) != len(vals):
                        touched = True; it = dict(it, secondary_any=ok)
                    kept.append(it)
                if len(kept) != len(items):
                    act[slot] = kept
            # an alt is unsatisfiable if a required slot was emptied
            if act.get("mode") == "exact" and not act.get("items") and act.get("mode") != "empty":
                broken.append((r["id"], ai, "exact items emptied"))
            if "must_have" in act and act.get("must_have") == [] and any(
                    s in json.dumps(a, ensure_ascii=False) for s in ()):
                pass
        # flex alt with an emptied one_of and no must_have left is unsatisfiable
        for ai, a in enumerate(r["alts"]):
            act = a["actions"]
            if act.get("mode") == "flex" and act.get("one_of") == [] and not act.get("must_have"):
                broken.append((r["id"], ai, "one_of emptied and no must_have"))
        if touched: changed.append(r["id"])
    Path(path).write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
    return changed, broken

for f in ["eval/testset.jsonl", "studies/round3/holdout-r3.jsonl"]:
    ch, br = fix(ROOT / f)
    print("%-36s 改动 %d 题: %s" % (f, len(ch), ch))
    print("%-36s 变得无法满足 %d 处: %s" % ("", len(br), br))
