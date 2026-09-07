#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力注册表：能力热更新的唯一来源。模型权重里不写能力表；prompt、约束解码的 JSON schema、验证器都从这里生成。

  python3 registry.py build            # 从 vocab.json 生成 capabilities.json（首次）
  python3 registry.py list             # 看状态
  python3 registry.py disable window.driver --reason "紧急下线"   # 下线一个能力
  python3 registry.py enable window.driver
  python3 registry.py render           # 生成 prompts/p3_grammar.generated.md（只含 enabled 能力）
  python3 registry.py schema           # 生成 schema.json（约束解码用，只含 enabled 能力）
"""
import json, os, sys, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "capabilities.json")

IDS = {
    "主驾车窗": ("window.driver", "driver window", "车窗", "B"), "副驾车窗": ("window.passenger", "passenger window", "车窗", "B"),
    "左后排车窗": ("window.rear_left", "rear left window", "车窗", "B"), "右后排车窗": ("window.rear_right", "rear right window", "车窗", "B"),
    "空调总开关": ("hvac.power", "climate power", "空调与空气", "A"), "MAX AC": ("hvac.max_ac", "MAX AC", "空调与空气", "A"),
    "AUTO模式": ("hvac.auto", "climate auto", "空调与空气", "A"), "前风窗除雾": ("hvac.defog_front", "front defog", "空调与空气", "A"),
    "内外循环设置": ("hvac.recirculation", "recirculation", "空调与空气", "A"), "自动空气净化": ("air.purify_auto", "auto air purifier", "空调与空气", "A"),
    "主驾座椅": ("seat.driver.occupied", "driver seat occupancy", "车辆状态", "A"), "副驾座椅": ("seat.passenger.occupied", "passenger seat occupancy", "车辆状态", "A"),
    "主驾座椅加热": ("seat.driver.heat", "driver seat heating", "座椅", "A"), "副驾座椅加热": ("seat.passenger.heat", "passenger seat heating", "座椅", "A"),
    "后左侧座椅加热": ("seat.rear_left.heat", "rear left seat heating", "座椅", "A"), "后右侧座椅加热": ("seat.rear_right.heat", "rear right seat heating", "座椅", "A"),
    "主驾座椅通风": ("seat.driver.vent", "driver seat ventilation", "座椅", "A"), "副驾座椅通风": ("seat.passenger.vent", "passenger seat ventilation", "座椅", "A"),
    "后左侧座椅通风": ("seat.rear_left.vent", "rear left seat ventilation", "座椅", "A"), "后右侧座椅通风": ("seat.rear_right.vent", "rear right seat ventilation", "座椅", "A"),
    "主驾座椅按摩": ("seat.driver.massage", "driver seat massage state", "车辆状态", "A"), "副驾座椅按摩": ("seat.passenger.massage", "passenger seat massage state", "车辆状态", "A"),
    "左前门": ("door.front_left", "front left door", "门", "B"), "右前门": ("door.front_right", "front right door", "门", "B"),
    "左后门": ("door.rear_left", "rear left door", "门", "B"), "右后门": ("door.rear_right", "rear right door", "门", "B"),
    "尾门": ("door.tailgate", "tailgate", "门", "B"), "前备箱": ("door.frunk", "frunk", "门", "B"),
    "香氛开关": ("fragrance.power", "fragrance", "氛围", "A"), "挡位": ("drive.gear", "gear", "车辆状态", "C"),
    "电量": ("battery.soc", "battery level", "车辆状态", "A"), "车速": ("vehicle.speed", "speed", "车辆状态", "A"),
    "车内温度": ("cabin.temp", "cabin temperature", "车辆状态", "A"), "车外温度": ("outside.temp", "outside temperature", "车辆状态", "A"),
    "车内PM2.5": ("cabin.pm25", "cabin PM2.5", "车辆状态", "A"),
    "主驾温度控制": ("hvac.temp.driver", "driver temperature", "空调与空气", "A"), "温区同步": ("hvac.sync", "zone sync", "空调与空气", "A"),
    "前排风量调节": ("hvac.fan.front", "front fan level", "空调与空气", "A"), "出风模式设置": ("hvac.mode", "air flow mode", "空调与空气", "A"),
    "AC开关": ("hvac.ac", "AC compressor", "空调与空气", "A"), "ECO": ("hvac.eco", "ECO", "空调与空气", "A"),
    "主驾模式": ("hvac.driver_only", "driver-only mode", "空调与空气", "A"), "空气自干燥": ("air.self_dry", "air self-dry", "空调与空气", "A"),
    "主驾座椅按摩强度": ("seat.driver.massage.level", "driver massage intensity", "座椅", "A"), "副驾座椅按摩强度": ("seat.passenger.massage.level", "passenger massage intensity", "座椅", "A"),
    "主驾座椅按摩模式": ("seat.driver.massage.mode", "driver massage mode", "座椅", "A"), "副驾座椅按摩模式": ("seat.passenger.massage.mode", "passenger massage mode", "座椅", "A"),
    "氛围灯开关": ("light.ambient.power", "ambient light", "氛围", "A"), "音乐律动": ("light.ambient.music_sync", "music sync lighting", "氛围", "A"),
    "氛围灯亮度": ("light.ambient.brightness", "ambient brightness", "氛围", "A"), "香氛类型": ("fragrance.type", "fragrance type", "氛围", "A"),
    "香氛浓度": ("fragrance.intensity", "fragrance intensity", "氛围", "A"), "方向盘加热": ("steering.heat", "steering wheel heating", "其他", "A"),
    "低速行人警报音": ("safety.avas", "pedestrian warning sound", "其他", "C"),
    "音乐播放": ("media.play_mood", "play music by mood", "声音", "A"), "音量": ("media.volume", "volume", "声音", "A"),
}

def load():
    return json.load(open(REG, encoding="utf-8"))

def save(reg):
    reg["version"] = datetime.now().strftime("%Y-%m-%d.%H%M")
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def build():
    vocab = json.load(open(os.path.join(HERE, "vocab.json"), encoding="utf-8"))
    caps = {}
    def put(zh, kind, values):
        cid, en, group, cls = IDS[zh]
        c = caps.setdefault(cid, {"id": cid, "zh": zh, "en": en, "group": group, "class": cls, "status": "enabled", "cond_values": None, "act_values": None, "deny_act_values": [], "notes": ""})
        c[kind] = values
    for zh, v in vocab["conditions"].items():
        put(zh, "cond_values", v)
    for zh, v in vocab["actions"].items():
        put(zh, "act_values", v)
    for zh, v in vocab.get("extensions_p2", {}).get("actions", {}).items():
        put(zh, "act_values", v); caps[IDS[zh][0]]["notes"] = "扩展能力，demo 原表没有"
    caps["safety.avas"]["deny_act_values"] = ["关闭"]; caps["safety.avas"]["notes"] = "AVAS 不允许自动化关闭（欧盟 R138、美国 FMVSS 141）"
    for cid in ("door.front_left", "door.front_right", "door.rear_left", "door.rear_right", "door.tailgate", "door.frunk", "drive.gear"):
        caps[cid]["notes"] = "只作条件，不作动作"
    save({"version": "", "capabilities": list(caps.values())})
    print("built", len(caps), "capabilities ->", REG)

def fmt_values(v):
    if isinstance(v, dict) and "range" in v:
        lo, hi, step, unit = v["range"]
        mid = lo + ((hi - lo) // 2 // max(step, 1)) * max(step, 1)
        return "%s 到 %s，如 %s%s" % (lo, hi, mid, unit)
    return "/".join(v)

def enabled(reg):
    return [c for c in reg["capabilities"] if c["status"] == "enabled"]

def render():
    reg = load(); caps = enabled(reg)
    conds = [c for c in caps if c["cond_values"]]
    sw = [c["zh"] for c in conds if c["cond_values"] == ["开启", "关闭"]]
    en = [c for c in conds if isinstance(c["cond_values"], list) and c["cond_values"] != ["开启", "关闭"]]
    num = [c for c in conds if isinstance(c["cond_values"], dict)]
    cond_txt = "开关型（开启/关闭）：" + "、".join(sw) + "\n枚举型：" + "、".join("%s（%s）" % (c["zh"], "/".join(c["cond_values"])) for c in en) + "\n数值型：" + "、".join("%s（%s）" % (c["zh"], fmt_values(c["cond_values"])) for c in num)
    acts = [c for c in caps if c["act_values"]]
    groups = {}
    for c in acts:
        groups.setdefault(c["group"], []).append(c)
    order = ["车窗", "空调与空气", "座椅", "氛围", "声音", "其他"]
    lines = []
    for g in order + [g for g in groups if g not in order]:
        if g not in groups: continue
        parts = []
        for c in groups[g]:
            v = c["act_values"]
            if c["deny_act_values"] and isinstance(v, list):
                v = [x for x in v if x not in c["deny_act_values"]]
            parts.append("%s（%s）" % (c["zh"], fmt_values(v)))
        lines.append("%s：%s" % (g, "、".join(parts)))
    act_txt = "\n".join(lines)
    tpl = open(os.path.join(HERE, "prompts", "p3_template.md"), encoding="utf-8").read()
    out = tpl.replace("{{CONDITIONS}}", cond_txt).replace("{{ACTIONS}}", act_txt).replace("{{VERSION}}", reg["version"])
    path = os.path.join(HERE, "prompts", "p3_grammar.generated.md")
    open(path, "w", encoding="utf-8").write(out)
    print("rendered", path, "conditions", len(conds), "actions", len(acts))

def schema():
    reg = load(); caps = enabled(reg)
    def val_schema(v, deny=()):
        if isinstance(v, dict) and "range" in v:
            return {"type": "string", "pattern": r"^-?\d+(\.\d+)?\S{0,6}$"}
        return {"enum": [x for x in v if x not in deny]}
    cond_items = [{"type": "object", "properties": {"primary": {"const": c["zh"]}, "op": {"enum": ["==", "<", "<=", ">", ">="]}, "secondary": val_schema(c["cond_values"])},
                   "required": ["primary", "op", "secondary"], "additionalProperties": False} for c in caps if c["cond_values"]]
    act_items = [{"type": "object", "properties": {"primary": {"const": c["zh"]}, "secondary": val_schema(c["act_values"], c["deny_act_values"])},
                  "required": ["primary", "secondary"], "additionalProperties": False} for c in caps if c["act_values"]]
    sch = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "scene_v3_" + reg["version"], "type": "object",
           "properties": {
               "relevance": {"type": "number", "minimum": 0, "maximum": 1},
               "intent": {"enum": ["action", "precise", "vague", "affect", "clarify", "none"]},
               "understanding": {"type": "string", "maxLength": 80},
               "name": {"type": "string", "maxLength": 10},
               "logic": {"enum": ["AND", "OR"]},
               "conditions": {"type": "array", "maxItems": 4, "items": {"oneOf": cond_items}},
               "actions": {"type": "array", "maxItems": 8, "items": {"oneOf": act_items}},
               "say": {"type": "string", "maxLength": 15},
               "offer": {"type": "object", "properties": {"type": {"enum": ["call", "navigate", "message", "none"]}, "target": {"type": "string", "maxLength": 20}}, "required": ["type"]},
               "memory": {"type": "array", "maxItems": 3, "items": {"type": "object", "properties": {"type": {"enum": ["preference", "relationship", "place", "dislike"]}, "content": {"type": "string", "maxLength": 80}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["type", "content", "confidence"]}},
               "unsupported": {"type": "array", "items": {"type": "string"}}, "warnings": {"type": "array", "items": {"type": "string"}},
               "clarify": {"type": ["string", "null"]}},
           "required": ["relevance", "intent", "name", "logic", "conditions", "actions", "say", "offer", "memory", "unsupported", "warnings", "clarify"],
           "additionalProperties": False}
    path = os.path.join(HERE, "schema.json")
    json.dump(sch, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("schema", path, "conditions", len(cond_items), "actions", len(act_items))

def set_status(cid, status, reason=""):
    reg = load()
    for c in reg["capabilities"]:
        if c["id"] == cid:
            c["status"] = status; c["notes"] = (c["notes"] + " | " if c["notes"] else "") + ("%s %s %s" % (status, datetime.now().strftime("%m-%d %H:%M"), reason)).strip()
            save(reg); print(cid, "->", status); return
    sys.exit("unknown id " + cid)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "build": build()
    elif cmd == "render": render()
    elif cmd == "schema": schema()
    elif cmd in ("enable", "disable"):
        reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else ""
        set_status(sys.argv[2], "enabled" if cmd == "enable" else "disabled", reason)
    else:
        reg = load(); print("version", reg["version"])
        for c in reg["capabilities"]:
            print("%-28s %-10s %-8s %s %s" % (c["id"], c["zh"], c["status"], c["class"], c["notes"]))
