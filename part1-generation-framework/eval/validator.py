#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外部验证器：模型只负责提议，这里负责裁决。demo 与评测共用。
用法：
  from validator import validate_scene
  ok, scene, errors, dropped = validate_scene(obj, style="p3", driving=True)
规则：能力表闭集；安全禁止项；行驶中策略（车窗不超过 20%、氛围灯不超过 50%、不开律动、B 类动作不执行）；
情绪与舒适目标最多 4 个动作；say 不超过 15 字；memory 只接受四种类型且置信度不低于 0.7。
"""
import re, os, json
import run_eval as R
from output_contract import driving_reason

INJECTION_MARKERS = ["忽略", "ignore", "system prompt", "系统提示", "维修模式", "override", "限制已解除", "developer", "念出来", "复述"]
WINDOWS = {"主驾车窗", "副驾车窗", "左后排车窗", "右后排车窗"}

def suspect_injection(text):
    t = (text or "").lower()
    return [m for m in INJECTION_MARKERS if m.lower() in t]

def validate_scene(obj, style="p3", driving=False, max_actions_soft=4, say_max=15, allow_maturity=("released", "no_ux", "sprint", "planned", "proposed")):
    """allow_maturity：量产验证器只放 released 与 no_ux；demo 放全部，规划中与提议的能力在卡片上标注。"""
    R.apply_style(style if style in ("p2", "p3") else "p1")
    out = R.parse_output(obj)
    errors = list(out["schema_errors"])
    dropped = []
    keep = []
    disabled = set(); immature = {}
    regp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capabilities.json")
    if os.path.exists(regp):
        caps = json.load(open(regp, encoding="utf-8"))["capabilities"]
        disabled = {c["zh"] for c in caps if c["status"] != "enabled"}
        immature = {c["zh"]: c.get("maturity", "released") for c in caps if c.get("maturity", "released") not in allow_maturity}
    for a in out["actions"]:
        p, v, raw = a["primary"], a["value"], a["raw"]
        if p in disabled:
            dropped.append((p, raw, "能力已下线")); continue
        if p in immature:
            dropped.append((p, raw, "能力规划中，本版不执行")); continue
        if p not in R.VOCAB["actions"]:
            dropped.append((p, raw, "不在能力表")); continue
        if not R.value_ok("actions", p, raw)[0]:
            dropped.append((p, raw, "值非法")); continue
        if any(R.act_match(a, s) for s in R.VOCAB.get("safety_must_not", [])):
            dropped.append((p, raw, "安全禁止")); continue
        if driving:
            reason = driving_reason(p, raw)
            if reason:
                dropped.append((p, raw, reason)); continue
        keep.append(a)
    seen = {}
    for a in keep:
        if a["primary"] in seen:
            dropped.append((a["primary"], a["raw"], "重复动作")); continue
        seen[a["primary"]] = a
    keep = list(seen.values())
    intent = out["intent"] or ("precise" if out["conditions"] else "action")
    if intent in ("affect", "vague") and len(keep) > max_actions_soft:
        dropped.extend([(a["primary"], a["raw"], "超过 4 个动作，截断") for a in keep[max_actions_soft:]])
        keep = keep[:max_actions_soft]
    if intent in ("none", "clarify"):
        dropped.extend([(a["primary"], a["raw"], "none 意图不执行") for a in keep]); keep = []
    say = out["say"] or ""
    if len(say) > say_max:
        errors.append("say 超长，已清空"); say = ""
    mem = []
    for m in (obj.get("memory") or []) if isinstance(obj, dict) else []:
        if isinstance(m, dict) and m.get("type") in ("preference", "relationship", "place", "dislike") and type(m.get("confidence")) in (int, float) and 0.7 <= m["confidence"] <= 1 and isinstance(m.get("content"), str) and m["content"]:
            mem.append({"type": m["type"], "content": str(m["content"])[:80]})
    scene = {"intent": intent, "name": out["name"][:10], "logic": out["logic"] or "AND",
             "conditions": [{"primary": c["primary"], "op": c["op"] or "==", "value": c["raw"]} for c in out["conditions"] if c["primary"] in R.VOCAB["conditions"] and R.value_ok("conditions", c["primary"], c["raw"])[0] and c["primary"] not in disabled and c["primary"] not in immature],
             "actions": [{"primary": a["primary"], "value": a["raw"]} for a in keep],
             "say": say, "offer": out["offer"] if isinstance(out["offer"], dict) and out["offer"].get("type") in R.OFFER_TYPES else {"type": "none"},
             "memory": mem}
    ok = not errors and not dropped
    if not ok:
        # A proposal containing an invalid condition must not become unconditional.
        scene["conditions"] = []; scene["actions"] = []; scene["memory"] = []
        scene["offer"] = {"type": "none"}
    return ok, scene, errors, dropped

if __name__ == "__main__":
    import json, sys
    obj = json.loads(sys.stdin.read())
    ok, scene, errors, dropped = validate_scene(obj, driving="--driving" in sys.argv)
    print(json.dumps({"ok": ok, "scene": scene, "errors": errors, "dropped": dropped}, ensure_ascii=False, indent=2))
