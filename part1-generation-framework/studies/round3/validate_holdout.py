import json, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
import registry
reg = registry.load()
CAP = {c["zh"]: c for c in reg["capabilities"] if c.get("status") == "enabled"}

def ok(cap, val, key):
    spec = cap.get(key)
    if spec is None:
        return False, "no %s" % key
    if isinstance(spec, list):
        return (val in spec), spec[:12]
    rng = spec.get("range")
    m = re.match(r"^(-?\d+(?:\.\d+)?)", str(val))
    if not m: return False, rng
    lo, hi, step, unit = rng
    if not str(val).endswith(unit): return False, "unit %s" % unit
    x = float(m.group(1))
    q = (x - lo) / step
    return (lo <= x <= hi and abs(q - round(q)) < 1e-6), rng

bad = []
rows = [json.loads(l) for l in Path("holdout-r3.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
for r in rows:
    for a in r["alts"]:
        for c in (a["conditions"].get("items") or []):
            cap = CAP.get(c["primary"])
            if not cap: bad.append((r["id"], "cond cap missing", c["primary"])); continue
            good, allowed = ok(cap, c["value"], "cond_values")
            if not good: bad.append((r["id"], "cond value", "%s=%s allowed=%s" % (c["primary"], c["value"], allowed)))
        acts = a["actions"]
        for it in (acts.get("items") or []) + (acts.get("must_have") or []) + (acts.get("one_of") or []) + (acts.get("must_not") or []) + (acts.get("acceptable") or []):
            cap = CAP.get(it["primary"])
            if not cap: bad.append((r["id"], "act cap missing", it["primary"])); continue
            for v in it.get("secondary_any") or []:
                good, allowed = ok(cap, v, "act_values")
                if not good: bad.append((r["id"], "act value", "%s=%s allowed=%s" % (it["primary"], v, allowed)))
print("cases:", len(rows), "problems:", len(bad))
for b in bad: print("  ", b[0], "|", b[1], "|", b[2])
