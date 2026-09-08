"""Pull the concrete cases the report needs, straight from the stored runs. No fabrication."""
import json, collections
from pathlib import Path

DEV_OOS = set("A01 A05 A09 A14 C05 C09 D02 F12 N01 N05 N10".split())
HO_OOS = set("R3H001 R3H002 R3H003 R3H004 R3H005 R3H007 R3H008 R3H009 R3H022 R3H039 R3H046 R3H047 R3H048 R3H049 R3H050".split())
OOS = DEV_OOS | HO_OOS

def load(run, f="raw.v4.jsonl"):
    p = Path(f"results/{run}/{f}")
    if not p.exists(): p = Path(f"results/{run}/raw.jsonl")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def index(runs):
    ix = {}
    for r in runs:
        for x in load(r):
            ix[(x["id"], x["lang"], x["variant"])] = x
    return ix

IX = index(["r3_12_p36", "r3_10_p35", "r3_09_p34", "r3_08_p33", "r3_05_equal",
            "r3_13_p36_holdout", "r3_11_holdout_final", "r3_06_holdout"])

def obj(rec):
    try: return json.loads(rec["raw_text"])
    except Exception: return None

def card(rec, label):
    o = obj(rec)
    if o is None: return {"arm": label, "unparsable": rec["raw_text"][:200]}
    return {"arm": label, "pass": rec["score"]["pass"], "schema_valid": rec["score"]["schema_valid"],
            "understanding": o.get("understanding"), "intent": o.get("intent"), "name": o.get("name"),
            "conditions": [(c.get("primary"), c.get("op"), c.get("secondary")) for c in (o.get("conditions") or [])],
            "actions": [(a.get("primary"), a.get("secondary")) for a in (o.get("actions") or [])],
            "say": o.get("say"), "memory": o.get("memory"), "warnings": o.get("warnings"),
            "fail_reason": rec["score"].get("fail_reason") or None,
            "violations": [str(v) for v in (rec["score"].get("violations") or [])]}

def compare(cid, lang, arms):
    rows = []
    for a in arms:
        r = IX.get((cid, lang, a))
        if r: rows.append(card(r, a))
    base = IX.get((cid, lang, arms[0]))
    return {"id": cid, "lang": lang, "cat": base["cat"] if base else None,
            "input": (base or {}).get("input"), "context": (base or {}).get("context") or None, "arms": rows}

OUT = {}
# 1. 三个梯度各一个真实例子
OUT["gradients"] = {
    "schema_fail_capability": compare("E08", "zh", ["v0_r3", "p36"]),
    "pass_fail_wrong_action": compare("C05", "zh", ["v0_r3", "p36"]) if ("C05","zh","p36") in IX else compare("C08", "zh", ["v0_r3", "p36"]),
    "safety_violation": compare("A10", "zh", ["v0_r3", "p36"]),
}
# 2. 每一步优化各一个真实的改变
OUT["optimisation_steps"] = {
    "p31_over_clarify_fixed_in_p33": compare("R3H017", "en", ["p31", "p33", "p36"]),
    "p31_memory_only_fixed_in_p33": compare("R3H060", "en", ["p31", "p33", "p36"]),
    "p33_understanding_overflow_fixed_in_p34": compare("G01", "en", ["p33", "p34", "p36"]),
    "p34_silent_refusal_fixed_in_p35": compare("F02", "zh", ["p34", "p35", "p36"]),
    "p35_attack_leak_fixed_in_p36": compare("R3H059", "en", ["p35", "p36"]),
}
# 3. 候选强于原版的代表案例
OUT["candidate_wins"] = {
    "grounding_uses_profile": compare("E01", "zh", ["v0_r3", "p36"]),
    "product_judgement_eco": compare("C08", "zh", ["v0_r3", "p36"]),
    "attack_refusal": compare("K08", "en", ["v0_r3", "p36"]),
}
# 4. 候选仍然失败的代表案例
fails = [r for r in load("r3_12_p36") if not r["score"]["pass"] and r["id"] not in OOS]
byreason = collections.Counter()
for r in fails:
    fr = r["score"].get("fail_reason") or ""
    key = "动作数量/多余动作" if ("动作数量" in fr or "多余动作" in fr or "动作过多" in fr) else \
          "意图判定" if "意图" in fr else \
          "条件不符" if "条件" in fr else \
          "契约长度" if ("契约" in fr or "太长" in fr) else "其它"
    byreason[key] += 1
OUT["candidate_failures"] = {"total": len(fails), "by_reason": dict(byreason),
    "samples": [{"id": r["id"], "lang": r["lang"], "cat": r["cat"], "input": r["input"],
                 "fail_reason": r["score"]["fail_reason"][:180]} for r in fails[:8]]}
Path("report-examples.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding="utf-8")
print("已抽取：", {k: len(v) if isinstance(v, dict) else v for k, v in OUT.items()})
print(json.dumps(OUT["candidate_failures"]["by_reason"], ensure_ascii=False))
