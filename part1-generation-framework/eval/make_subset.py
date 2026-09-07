#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 testset.jsonl 里按类别等距抽一个核心子集，用于迭代与消融的单轮快跑。
不改 testset.jsonl，只做确定性过滤：每类按 id 排序后等距取 k 条，attack 与 clarify 全取。
  python3 make_subset.py --out testset_core.jsonl
"""
import argparse, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
# 每类取几条；attack、clarify 取满（安全与追问是门槛项）
QUOTA = {"attack": 99, "clarify": 99, "action": 7, "precise": 9, "vague": 5, "affect": 6,
         "robust": 5, "weak": 4, "memory": 4, "observe": 3, "explicit": 5}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="testset.jsonl")
    ap.add_argument("--out", default="testset_core.jsonl")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(os.path.join(HERE, a.src), encoding="utf-8") if l.strip()]
    by = {}
    for r in rows:
        by.setdefault(r["cat"], []).append(r)
    picked = []
    for cat, rs in by.items():
        rs.sort(key=lambda r: r["id"])
        k = min(QUOTA.get(cat, 3), len(rs))
        if k >= len(rs):
            picked += rs
        else:
            step = len(rs) / k
            picked += [rs[int(i * step)] for i in range(k)]
    picked.sort(key=lambda r: r["id"])
    with open(os.path.join(HERE, a.out), "w", encoding="utf-8") as f:
        for r in picked:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print("子集 %d 题：%s" % (len(picked), dict(Counter(r["cat"] for r in picked))))
    print("ids:", " ".join(r["id"] for r in picked))

if __name__ == "__main__":
    main()
