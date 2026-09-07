#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""消融：从一份模板出发，每次只拿掉或替换一段，渲染成可跑的 prompt。
  python3 run_ablation.py --base prompts/p4_r0X.tpl.md --list
  python3 run_ablation.py --base prompts/p4_r0X.tpl.md --make no-grammar --out prompts/abl/no-grammar.md
只生成 prompt，不跑模型；跑用 run_eval.py。"""
import argparse, os, re, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))

def sections(txt):
    """按 '## ' 切段，返回 [(heading, body_including_heading)]"""
    parts = re.split(r'(?m)^(## .*)$', txt)
    out = [("__head__", parts[0])]
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i] + parts[i + 1]))
    return out

def drop_section(txt, name):
    secs = sections(txt)
    hit = [h for h, _ in secs if h.startswith("## " + name)]
    if not hit:
        sys.exit("找不到段落 %s，现有：%s" % (name, [h for h, _ in secs]))
    return "".join(b for h, b in secs if not h.startswith("## " + name))

def n_examples(txt, n):
    secs = sections(txt)
    out = []
    for h, b in secs:
        if h.startswith("## 示例"):
            head, rest = b.split("\n", 1)
            blocks = [x for x in re.split(r'\n(?=输入：|Input: )', rest) if x.strip()]
            b = head + "\n" + "\n".join(blocks[:n]) + ("\n" if n else "")
            if n == 0:
                b = ""
        out.append(b)
    return "".join(out)

def understanding_last(txt):
    """把 understanding 从输出格式的首字段挪到末字段，示例里同步挪。"""
    m = re.search(r'^  "understanding".*\n', txt, re.M)
    if not m:
        sys.exit("找不到 understanding 行")
    txt = txt.replace(m.group(0), "", 1)
    m2 = re.search(r'^  "clarify".*\n', txt, re.M)
    if not m2:
        sys.exit("找不到 clarify 行")
    txt = txt.replace(m2.group(0), m2.group(0).rstrip("\n") + ",\n" +
                      '  "understanding": "永远是最后一个字段。一句话说这个人此刻需要什么，必须引用用户原话里的词；intent 为 none 时可为空"\n', 1)
    txt = txt.replace("永远是第一个字段。", "永远是最后一个字段。")
    txt = txt.replace("3. understanding 先写，动作要能从 understanding 推出来。",
                      "3. understanding 最后写，动作要能从 understanding 推出来。")
    def fix(mm):
        try:
            o = json.loads(mm.group(0))
        except Exception:
            return mm.group(0)
        if "understanding" not in o:
            return mm.group(0)
        u = o.pop("understanding"); o["understanding"] = u
        return json.dumps(o, ensure_ascii=False)
    txt = re.sub(r'\{"understanding".*\}', fix, txt)
    return txt

RECIPES = {
    "no-grammar":     ("删掉六元素语法段", lambda t: drop_section(t, "布景的语法")),
    "no-safety":      ("删掉安全硬规则段", lambda t: drop_section(t, "安全硬规则")),
    "no-memory":      ("删掉记忆建议段", lambda t: drop_section(t, "记忆建议")),
    "no-examples":    ("0 条示例", lambda t: n_examples(t, 0)),
    "ex3":            ("示例减到 3 条", lambda t: n_examples(t, 3)),
    "ex4":            ("示例减到 4 条", lambda t: n_examples(t, 4)),
    "ex5":            ("示例减到 5 条", lambda t: n_examples(t, 5)),
    "no-format":      ("删掉输出格式段的字段注释", lambda t: drop_section(t, "输出格式")),
    "no-intent":      ("删掉意图定义段", lambda t: drop_section(t, "意图")),
    "no-rules":       ("删掉其他规则段", lambda t: drop_section(t, "其他规则")),
    "und-last":       ("understanding 挪到末尾", understanding_last),
    "no-anticollapse":("删掉反坍缩段", lambda t: drop_section(t, "不要坍缩")),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--make", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, (d, _) in RECIPES.items(): print("%-16s %s" % (k, d))
        return
    txt = open(os.path.join(HERE, a.base), encoding="utf-8").read()
    txt = RECIPES[a.make][1](txt)
    tmp = os.path.join(HERE, "prompts", "abl", "_tpl_%s.md" % a.make)
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "w", encoding="utf-8").write(txt)
    out = a.out or os.path.join("prompts", "abl", a.make + ".md")
    subprocess.check_call([sys.executable, os.path.join(HERE, "registry.py"), "render", "--template", tmp, "--out", os.path.join(HERE, out)])
    print("消融版本：", out, RECIPES[a.make][0])

if __name__ == "__main__":
    main()
