"""Side-by-side v0 / v3 / p36 on the same item, straight from the stored runs."""
import json, sys
sys.path.insert(0, ".")
from report_tables import load

def index(run):
    return {(r["id"], r["lang"], r["variant"]): r for r in load(run)}

BASE = index("r3_05_equal"); CAND = index("r3_12_p36")
HB = index("r3_06_holdout"); HC = index("r3_13_p36_holdout")

def show(qid, lang="zh"):
    src_b = BASE if (qid, lang, "v0_r3") in BASE else HB
    src_c = CAND if (qid, lang, "p36") in CAND else HC
    ref = src_b.get((qid, lang, "v0_r3"))
    if not ref: print(f"{qid}: 无"); return
    print("=" * 78)
    print(f'{qid} [{ref["cat"]}/{lang}]  输入：{ref["input"]}')
    if ref.get("context"): print(f'  上下文：{ref["context"][:220]}')
    for label, r in (("v0_r3 同事原版", src_b.get((qid, lang, "v0_r3"))),
                     ("v3_r3 第一轮基线", src_b.get((qid, lang, "v3_r3"))),
                     ("p36 定版", src_c.get((qid, lang, "p36")))):
        if not r: continue
        p = (r["score"].get("parsed") or {})
        ok = "通过" if r["score"].get("pass") else "未通过"
        print(f'\n  --- {label}  [{ok}]  {r["score"].get("fail_reason","") or ""}')
        print(f'      understanding: {p.get("understanding")!r}')
        print(f'      intent={p.get("intent")} relevance={p.get("relevance")} name={p.get("name")!r}')
        norm = lambda xs: [tuple(x) if isinstance(x, list) else tuple(x.values()) for x in (xs or [])]
        print(f'      conditions: {norm(p.get("conditions"))}')
        print(f'      actions:    {norm(p.get("actions"))}')
        print(f'      say: {p.get("say")!r}  warnings={p.get("warnings")} unsupported={p.get("unsupported")} clarify={p.get("clarify")!r}')

if __name__ == "__main__":
    args = sys.argv[1:]
    for a in args:
        qid, _, lang = a.partition(":")
        show(qid, lang or "zh")
