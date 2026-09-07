#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一次评测运行导出成原型页能回放的 cases.json：真实的模型输出、真实的时延、验证器裁掉了什么。
  python3 export_cases.py --tag smoke-kimi-k27-p3-zh --out ../demo/gen-app/cases.json
  python3 export_cases.py --tag a,b --ids F03,G07,J01 --out ../demo/gen-app/cases.json
"""
import argparse, json, os
import run_eval as R
from validator import validate_scene
HERE = os.path.dirname(os.path.abspath(__file__))
ELEMENT = {}
for p in ["氛围灯开关", "氛围灯亮度", "音乐律动"]: ELEMENT[p] = "光"
for p in ["音乐播放", "音量"]: ELEMENT[p] = "声"
for p in ["香氛开关", "香氛类型", "香氛浓度", "自动空气净化", "内外循环设置", "空气自干燥", "主驾车窗", "副驾车窗", "左后排车窗", "右后排车窗"]: ELEMENT[p] = "气"
def element(p): return ELEMENT.get(p, "温")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--ids", default=""); ap.add_argument("--lang", default="both")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "demo", "gen-app", "cases.json")); a = ap.parse_args()
    R.apply_style("p3"); want = set(a.ids.split(",")) if a.ids else None; cases = []
    for tag in a.tag.split(","):
        S = json.load(open(os.path.join(HERE, "results", tag, "summary.json"), encoding="utf-8"))
        for l in open(os.path.join(HERE, "results", tag, "raw.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            if r["rep"] != 0 or (want and r["id"] not in want) or (a.lang != "both" and r["lang"] != a.lang): continue
            obj = R.extract_json(r["raw_text"]) if r["raw_text"] else None
            if not isinstance(obj, dict): continue
            driving = "行驶中" in (r.get("context") or "") or "driving" in (r.get("context") or "")
            ok, scene, errors, dropped = validate_scene(obj, "p3", driving=driving)
            kept = {(x["primary"], str(x["value"])) for x in scene["actions"]}
            acts = []
            for x in obj.get("actions") or []:
                if not isinstance(x, dict): continue
                p, v = str(x.get("primary")), str(x.get("secondary"))
                d = next((dd for dd in dropped if dd[0] == p), None)
                acts.append({"element": element(p), "primary": p, "value": v, "dropped": bool(d and (p, v) not in kept), "reason": d[2] if d else ""})
            cases.append({"id": r["id"], "cat": r["cat"], "lang": r["lang"], "model": S.get("model_key") or S["model"], "prompt": S["prompt"],
                          "input": r["input"], "context": r.get("context") or "", "driving": driving,
                          "latency": round(r["latency"], 2), "ttft": round(r["ttft"] or 0, 2), "t_und": round(r.get("t_und") or r["latency"], 2),
                          "understanding": obj.get("understanding", ""), "name": obj.get("name", ""), "intent": obj.get("intent"), "relevance": obj.get("relevance"),
                          "conditions": [{"primary": c.get("primary"), "op": c.get("op", "=="), "value": c.get("secondary")} for c in obj.get("conditions") or [] if isinstance(c, dict)],
                          "actions": acts, "say": obj.get("say", ""), "offer": obj.get("offer"), "memory": obj.get("memory") or [], "unsupported": obj.get("unsupported") or [],
                          "warnings": obj.get("warnings") or [], "clarify": obj.get("clarify"), "validator_ok": ok, "pass": r["score"]["pass"], "fail_reason": r["score"]["fail_reason"]})
    json.dump(cases, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(len(cases), "cases ->", a.out)
main()
