"""Pull concrete judge ratings with their stated reasons, straight from the stored reviews."""
import json, collections, sys
from pathlib import Path

DIMS = ("grounding", "restraint", "wording", "composition")
ZH = {"grounding": "贴切", "restraint": "分寸", "wording": "话术", "composition": "组合"}


def load(name):
    samples = {s["sample_id"]: s for s in json.loads(Path(f"judge/{name}-samples.json").read_text(encoding="utf-8"))}
    rows = [json.loads(l) for l in Path(f"judge/{name}/raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for r in rows:
        if r.get("error") or not r.get("rating"):
            continue
        s = samples.get(r["sample_id"])
        if not s:
            continue
        cand, base = ("A", "B") if s["candidate_position"] == "A" else ("B", "A")
        ra, rb = r["rating"].get(cand) or {}, r["rating"].get(base) or {}
        if not all(d in ra and d in rb for d in DIMS):
            continue
        out.append(dict(sample=s, model=r["model"], pos=s["candidate_position"],
                        cand={d: ra[d] for d in DIMS}, base={d: rb[d] for d in DIMS},
                        cand_why=ra.get("evidence", ""), base_why=rb.get("evidence", ""),
                        cand_out=s[cand], base_out=s[base],
                        total=sum(ra[d] - rb[d] for d in DIMS)))
    return out


def report(name, top=4):
    rec = load(name)
    rec.sort(key=lambda x: -x["total"])
    print("#" * 78); print(name, f"（有效 {len(rec)} 条）")
    for label, sub in (("候选赢得最多", rec[:top]), ("候选输得最多", rec[-top:][::-1])):
        print(f"\n===== {label} =====")
        for x in sub:
            s = x["sample"]
            print(f'\n--- {s["id"]} [{s["locale"]}/{s["cat"]}] 评委 {x["model"]} 候选在 {x["pos"][0] if x["pos"]=="A" else "B"} 位 合计差 {x["total"]:+d}')
            print(f'  输入：{s["input"]}')
            if s.get("context"):
                print(f'  上下文：{s["context"][:200]}')
            print(f'  候选四维 {[x["cand"][d] for d in DIMS]}  对照四维 {[x["base"][d] for d in DIMS]}   (顺序 贴切/分寸/话术/组合)')
            print(f'  候选 understanding：{x["cand_out"].get("understanding")}')
            print(f'  候选 say：{x["cand_out"].get("say")!r}  actions：{[(a["primary"],a["secondary"]) for a in x["cand_out"].get("actions",[])]}')
            print(f'  对照 understanding：{x["base_out"].get("understanding")}')
            print(f'  对照 say：{x["base_out"].get("say")!r}  actions：{[(a["primary"],a["secondary"]) for a in x["base_out"].get("actions",[])]}')
            print(f'  评委说候选：{x["cand_why"]}')
            print(f'  评委说对照：{x["base_why"]}')


if __name__ == "__main__":
    for n in sys.argv[1:] or ["dev-p36-vs-v0"]:
        report(n)
