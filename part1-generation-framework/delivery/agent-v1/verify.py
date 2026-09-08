#!/usr/bin/env python3
"""交付包自检：不发生任何模型调用，只验证这个包自身是自洽的。

    SCENE_CAPS=r3 SCENE_CONTRACT=v4 python3 verify.py

依次检查：提示词与冻结哈希一致、提示词的能力段与注册表没有漂移、
Schema 能从注册表渲染出来、六类门控各自拦对了东西。
"""
import json, os, sys, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("SCENE_CAPS", "r3")
os.environ.setdefault("SCENE_CONTRACT", "v4")
sys.path.insert(0, str(HERE / "gates"))
sys.path.insert(0, str(HERE / "runtime"))
import core  # noqa: E402

FROZEN = json.loads((HERE / "FINAL-p36.json").read_text(encoding="utf-8"))
REG = json.loads((HERE / "registry/capabilities.json").read_text(encoding="utf-8"))
SNAP = {
    "version": REG["version"],
    "revision": core.digest({"generation": 0, "capabilities": [
        {k: c.get(k) for k in ("id", "zh", "status", "cond_values", "act_values")}
        for c in REG["capabilities"]]}),
    "capabilities": REG["capabilities"],
}

ok = True
def check(label, got, want):
    global ok
    good = got == want
    ok = ok and good
    print("  %s %-46s %s" % ("通过" if good else "不通过", label, got))

print("\n[1] 提示词与注册表")
prompt = (HERE / "prompt/p36_zh.md").read_text(encoding="utf-8")
check("提示词哈希 == 冻结记录", hashlib.sha256(prompt.encode()).hexdigest()[:16],
      FROZEN["prompt"]["sha256"][:16])
text, meta = core.compile_prompt(SNAP, HERE / "prompt/p36_zh.md")
check("下发的提示词与被评测的逐字节一致", text == prompt, True)
check("能力段相对注册表无漂移", meta["table"], "verified-in-place")
check("注册表条数", len(REG["capabilities"]), 114)

print("\n[2] 输出契约")
schema = core.output_schema(SNAP)
check("Schema 顶层字段数", len(schema["properties"]), 15)
check("禁止额外字段", schema.get("additionalProperties"), False)

print("\n[3] 门控")
base = {"understanding": "车里有点凉，先把主驾座椅加热开到1挡", "relevance": 0.8,
        "intent": "vague", "name": "暖座", "logic": "AND", "conditions": [],
        "actions": [{"primary": "主驾座椅加热", "secondary": "1挡"}],
        "say": "座椅加热开到1挡了", "offer": {"type": "none", "target": ""},
        "memory": [], "unsupported": [], "warnings": [], "clarify": None}
CASES = [
    ("合法卡片放行",            base, None, True),
    ("关闭 AVAS 被拦",          dict(base, actions=[{"primary": "低速行人警报音", "secondary": "关闭"}]), None, False),
    ("行驶中开窗 100% 被拦",     dict(base, actions=[{"primary": "主驾车窗", "secondary": "100%"}]), {"driving": True}, False),
    ("自造能力被拦",            dict(base, actions=[{"primary": "媒体音量", "secondary": "0%"}]), None, False),
    ("已剔除取值被拦",           dict(base, actions=[{"primary": "主驾座椅按摩模式", "secondary": "波浪"}]), None, False),
    ("中文 say 超 30 字符被拦",  dict(base, say="这是一句故意写得非常长的回应用来测试契约长度上限是否真的会被拦下来一二三四五"), None, False),
    ("英文 say 39 字符放行",     dict(base, say="Seat heating is on at level two for you"), None, True),
]
for label, raw, ctx, want in CASES:
    r = core.validate(raw, SNAP, context=ctx)
    blocked = [d for d in r["decisions"] if d.get("status") == "blocked"]
    got = r["valid"] and r["executable"]
    reason = blocked[0]["reason"][:38] if blocked else ""
    global_ok = got == want
    ok = ok and global_ok
    print("  %s %-24s valid=%-5s executable=%-5s %s"
          % ("通过" if global_ok else "不通过", label, r["valid"], r["executable"], reason))

print("\n" + ("自检全部通过。" if ok else "自检未通过。"))
sys.exit(0 if ok else 1)
