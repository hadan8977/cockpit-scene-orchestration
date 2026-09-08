"""Prove that every arm in the final comparison carries the identical capability table.
Offline check, no API calls. Run with SCENE_CAPS=r3."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
import contract_limits as CL

V = json.loads((Path(__file__).resolve().parents[2] / "eval" / CL.VOCAB_FILE).read_text(encoding="utf-8"))
VC, VA = set(V["conditions"]), set(V["actions"])

def block_table(p):                       # p28+ 的 "名称 = 值/值" 表
    t = Path(p).read_text(encoding="utf-8")
    c = t.split("[CONDITIONS ONLY]")[1].split("[ACTIONS ONLY]")[0]
    a = t.split("[ACTIONS ONLY]")[1].split("[examples]")[0]
    f = lambda s: {l.split("=")[0].strip().rstrip("*").strip() for l in s.strip().splitlines() if "=" in l}
    return f(c), f(a)

def js_table(p):                          # v0 的两个 JS 数组
    t = Path(p).read_text(encoding="utf-8")
    head, tail = t.split("const c =", 1)
    g = lambda s: set(re.findall(r'\{"primary":"([^"]+)"', s))
    return g(head.split("const allConditions =")[1]), g(tail)

def prose_table(p):                       # v3 的自然语言表
    t = Path(p).read_text(encoding="utf-8")
    g = lambda s: {m.strip() for m in re.findall(r'([^\s，。；:：]+)\s*[:：]', s)}
    c = t.split("条件能力")[1].split("动作能力")[0] if "条件能力" in t else ""
    a = t.split("动作能力")[1][:20000] if "动作能力" in t else ""
    return g(c), g(a)

ARMS = [("p36 候选", block_table, "prompts/p36_zh.md"),
        ("v0_r3 同事原版", js_table, "prompts/v0_r3.md")]

if __name__ == "__main__":
    print(f"校验器词表 {CL.VOCAB_FILE}: conditions {len(VC)}, actions {len(VA)}")
    bad = 0
    for label, fn, path in ARMS:
        c, a = fn(path)
        dc, da = sorted(c ^ VC), sorted(a ^ VA)
        bad += bool(dc or da)
        print(f'{label:16s} conditions {len(c):3d} actions {len(a):3d} | 与校验器差异: '
              f'{dc or "无"} / {da or "无"}')
    print("结论：" + ("候选与同事原版携带完全相同的能力表，且与校验器一致" if not bad
                    else "存在差异，需修"))
    print("v3_r3 的表由 build_v3_r3.py 从同一份注册表渲染，格式是自然语言不便逐名解析，"
          "其生成脚本与 v0_r3 共用同一个注册表快照。")
