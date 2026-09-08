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
import contract_limits as CL

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, CL.CAPS_FILE)

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
    "时段": ("ctx.time_of_day", "time of day", "条件语义", "A"), "星期类型": ("ctx.day_type", "day type", "条件语义", "A"),
    "地点": ("ctx.place", "place class", "条件语义", "A"), "天气": ("ctx.weather", "weather", "条件语义", "A"),
    "行程事件": ("ctx.trip_event", "trip event", "条件语义", "A"),
}

def load():
    return json.load(open(REG, encoding="utf-8"))

def save(reg):
    reg["version"] = datetime.now().strftime("%Y-%m-%d.%H%M")
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

SLUG = {"车窗": "window", "空调与空气": "hvac", "乘员": "occupant", "座椅": "seat", "门": "door", "氛围": "ambient", "车辆状态": "vehicle", "环境": "env",
        "灯光": "light", "声音": "audio", "设备": "device", "条件语义": "ctx", "话": "voice", "编排": "flow", "供": "offer", "惊喜": "surprise", "预设": "preset", "屏幕": "screen", "其他": "misc", "生效范围": "scope", "娱乐": "app"}

def _id(zh, group, kind):
    if zh in IDS: return IDS[zh][0]
    base = SLUG.get(group, "x") + "." + re.sub(r"[^a-z0-9]+", "_", zh.lower()).strip("_")
    if not re.search(r"[a-z0-9]", base.split(".")[1]):
        base = SLUG.get(group, "x") + "." + "c%04x" % (sum(ord(ch) for ch in zh) % 0xffff)
    return base

def build():
    """从 vocab.json（v2，带 meta）生成 capabilities.json；已有条目保留 status 与 notes。"""
    vocab = json.load(open(os.path.join(HERE, "vocab.json"), encoding="utf-8"))
    old = {c["id"]: c for c in load()["capabilities"]} if os.path.exists(REG) else {}
    meta = vocab.get("meta", {"conditions": {}, "actions": {}})
    caps = {}
    def put(zh, kind, values):
        m = meta[kind].get(zh, {})
        group = m.get("group") or (IDS[zh][2] if zh in IDS else "其他")
        cid = m.get("id") or _id(zh, group, kind)
        en = m.get("en") or (IDS[zh][1] if zh in IDS else zh)
        c = caps.setdefault(cid, {"id": cid, "zh": zh, "en": en, "group": group, "class": m.get("class") or (IDS[zh][3] if zh in IDS else "A"), "status": "enabled",
                                  "maturity": m.get("maturity", "released"), "source": m.get("source", ""), "exec": m.get("exec", ""), "cond_values": None, "act_values": None, "deny_act_values": [], "notes": m.get("note", "")})
        c[{"conditions": "cond_values", "actions": "act_values"}[kind]] = values
        if kind == "actions" and m.get("maturity") and c["maturity"] == "released" and m["maturity"] != "released":
            c["maturity"] = m["maturity"]
        if cid in old:
            c["status"] = old[cid]["status"]
            if old[cid].get("notes") and "演练" in old[cid]["notes"]: c["notes"] = (c["notes"] + " | " if c["notes"] else "") + old[cid]["notes"]
    for zh, v in vocab["conditions"].items(): put(zh, "conditions", v)
    for zh, v in vocab["actions"].items(): put(zh, "actions", v)
    for s_ in vocab.get("safety_must_not", []):
        for c in caps.values():
            if c["zh"] == s_["primary"]: c["deny_act_values"] = list(s_["secondary_any"])
    save({"version": "", "capabilities": list(caps.values())})
    from collections import Counter
    print("built", len(caps), "capabilities ->", REG, dict(Counter(c["maturity"] for c in caps.values())))

def sync():
    """把 vocab.json 里新增的能力并入已有注册表，不动已有条目的状态与备注。"""
    vocab = json.load(open(os.path.join(HERE, "vocab.json"), encoding="utf-8"))
    reg = load(); have = {c["id"] for c in reg["capabilities"]}; added = 0
    def put(zh, kind, values, note=""):
        nonlocal added
        cid, en, group, cls = IDS[zh]
        c = next((x for x in reg["capabilities"] if x["id"] == cid), None)
        if c is None:
            c = {"id": cid, "zh": zh, "en": en, "group": group, "class": cls, "status": "enabled", "cond_values": None, "act_values": None, "deny_act_values": [], "notes": note}
            reg["capabilities"].append(c); added += 1
        if c[kind] is None: c[kind] = values
    for zh, val in vocab.get("extensions_p3", {}).get("conditions", {}).items():
        put(zh, "cond_values", val, "条件语义层第一批，只作条件")
    save(reg); print("synced, added", added, "->", REG)

def fmt_values(v):
    if isinstance(v, dict) and "range" in v:
        lo, hi, step, unit = v["range"]
        mid = lo + ((hi - lo) // 2 // max(step, 1)) * max(step, 1)
        return "%s 到 %s，如 %s%s" % (lo, hi, mid, unit)
    return "/".join(v)

def enabled(reg):
    return [c for c in reg["capabilities"] if c["status"] == "enabled"]

MAT_TAG = {"released": "", "no_ux": "", "sprint": "（规划中）", "planned": "（规划中）", "proposed": "（提议，需共建）"}

def _compact(vals):
    """把 关闭/10%/20%/.../100% 这类逐个枚举压成区间写法。"""
    if not isinstance(vals, list): return None
    pcts = [v for v in vals if isinstance(v, str) and v.endswith("%") and v[:-1].isdigit()]
    if len(pcts) >= 5:
        rest = [v for v in vals if v not in pcts]
        nums = sorted(int(v[:-1]) for v in pcts)
        step = nums[1] - nums[0] if len(nums) > 1 else 10
        rng = "%d%% 到 %d%% 步长 %d%%" % (nums[0], nums[-1], step)
        return "/".join(rest + [rng]) if rest else rng
    lv = [v for v in vals if isinstance(v, str) and re.fullmatch(r"\d+挡", v)]
    if len(lv) >= 5:
        rest = [v for v in vals if v not in lv]
        nums = sorted(int(v[:-1]) for v in lv)
        return "/".join(rest + ["%d挡 到 %d挡" % (nums[0], nums[-1])])
    return None

def render(tpl_path=None, out_path=None, caps_mode="text"):
    reg = load(); caps = enabled(reg)
    conds = [c for c in caps if c["cond_values"]]
    sw = [c["zh"] + MAT_TAG.get(c.get("maturity", "released"), "") for c in conds if c["cond_values"] == ["开启", "关闭"]]
    en = [c for c in conds if isinstance(c["cond_values"], list) and c["cond_values"] != ["开启", "关闭"]]
    num = [c for c in conds if isinstance(c["cond_values"], dict)]
    def V(v):
        if caps_mode == "compact":
            c = _compact(v)
            if c: return c
        return fmt_values(v)
    cond_txt = "开关型（开启/关闭）：" + "、".join(sw) + "\n枚举型：" + "、".join("%s%s（%s）" % (c["zh"], MAT_TAG.get(c.get("maturity", "released"), ""), V(c["cond_values"])) for c in en) + "\n数值型：" + "、".join("%s（%s）" % (c["zh"], fmt_values(c["cond_values"])) for c in num)
    acts = [c for c in caps if c["act_values"]]
    groups = {}
    for c in acts:
        groups.setdefault(c["group"], []).append(c)
    order = ["空调与空气", "座椅", "车窗", "门", "氛围", "声音", "娱乐", "话", "供", "预设", "惊喜", "屏幕", "设备", "编排", "其他"]
    lines = []
    for g in order + [g for g in groups if g not in order]:
        if g not in groups: continue
        parts = []
        for c in groups[g]:
            v = c["act_values"]
            if c["deny_act_values"] and isinstance(v, list):
                v = [x for x in v if x not in c["deny_act_values"]]
            parts.append("%s%s（%s）" % (c["zh"], MAT_TAG.get(c.get("maturity", "released"), ""), V(v)))
        lines.append("%s：%s" % (g, "、".join(parts)))
    act_txt = "\n".join(lines)
    if caps_mode == "json":
        cond_txt = json.dumps([{"n": c["zh"] + MAT_TAG.get(c.get("maturity", "released"), ""), "v": c["cond_values"]} for c in conds], ensure_ascii=False)
        act_txt = json.dumps([{"n": c["zh"] + MAT_TAG.get(c.get("maturity", "released"), ""), "g": c["group"],
                               "v": [x for x in c["act_values"] if x not in (c["deny_act_values"] or [])] if isinstance(c["act_values"], list) else c["act_values"]} for c in acts], ensure_ascii=False)
    tpl = open(tpl_path or os.path.join(HERE, "prompts", "p3_template.md"), encoding="utf-8").read()
    out = tpl.replace("{{CONDITIONS}}", cond_txt).replace("{{ACTIONS}}", act_txt).replace("{{VERSION}}", reg["version"])
    path = out_path or os.path.join(HERE, "prompts", "p3_grammar.generated.md")
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
               "understanding": {"type": "string", "maxLength": CL.UNDERSTANDING_MAX},
               "relevance": {"type": "number", "minimum": 0, "maximum": 1},
               "intent": {"enum": ["action", "precise", "vague", "affect", "observation", "clarify", "none"]},
               "name": {"type": "string", "maxLength": CL.NAME_MAX},
               "logic": {"enum": ["AND", "OR"]},
               "conditions": {"type": "array", "maxItems": 4, "items": {"oneOf": cond_items}},
               "actions": {"type": "array", "maxItems": 8, "items": {"oneOf": act_items}},
               "say": {"type": "string", "maxLength": CL.SAY_MAX},
               "offer": {"type": "object", "properties": {"type": {"enum": ["call", "navigate", "message", "none"]}, "target": {"type": "string", "maxLength": 20}}, "required": ["type"]},
               "memory": {"type": "array", "maxItems": 3, "items": {"type": "object", "properties": {"type": {"enum": ["preference", "relationship", "place", "dislike"]}, "content": {"type": "string", "maxLength": 80}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["type", "content", "confidence"]}},
               "unsupported": {"type": "array", "items": {"type": "string"}}, "warnings": {"type": "array", "items": {"type": "string"}},
               "clarify": {"type": ["string", "null"]}},
           "required": ["understanding", "relevance", "intent", "name", "logic", "conditions", "actions", "say", "offer", "memory", "unsupported", "warnings", "clarify"],
           "additionalProperties": False}
    path = os.path.join(HERE, CL.SCHEMA_FILE)
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
    elif cmd == "sync": sync()
    elif cmd == "render":
        a = sys.argv[2:]
        tp = a[a.index("--template") + 1] if "--template" in a else None
        op = a[a.index("--out") + 1] if "--out" in a else None
        cm = a[a.index("--caps") + 1] if "--caps" in a else "text"
        render(tp, op, cm)
    elif cmd == "schema": schema()
    elif cmd in ("enable", "disable"):
        reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else ""
        set_status(sys.argv[2], "enabled" if cmd == "enable" else "disabled", reason)
    else:
        reg = load(); print("version", reg["version"])
        for c in reg["capabilities"]:
            print("%-32s %-10s %-8s %s %-9s %s" % (c["id"], c["zh"], c["status"], c["class"], c.get("maturity", ""), c["notes"][:60]))
