"""Blind-review summary across the whole round-three candidate chain. Offline."""
import sys, json
sys.path.insert(0, ".")
import analysis

ZH = {"grounding": "贴切", "restraint": "分寸", "wording": "话术", "composition": "组合"}

def show(name, models=("dsv4", "qwen", "luna")):
    try:
        r = analysis.review(name)
    except Exception as e:
        print(f"{name}: 无结果 ({e})"); return
    print("=" * 78); print(name)
    for m in models:
        d = r.get(m)
        if not d: continue
        print(f'  {m:5s} 有效 {d["valid"]}/{d["expected"]}  题簇 {d["dimensions"]["grounding"]["n_clusters"]}')
        for k in ("grounding", "restraint", "wording", "composition"):
            v = d["dimensions"][k]
            star = " ✅" if v["ci95"][0] > 0 else (" ❌" if v["ci95"][1] < 0 else "")
            print(f'      {ZH[k]}  Δ{v["delta"]:+.3f}  [{v["ci95"][0]:+.3f}, {v["ci95"][1]:+.3f}]  '
                  f'Holm p={v["p_holm"]:.3f}  候选{v["candidate"]:.2f} 对照{v["baseline"]:.2f}{star}')

if __name__ == "__main__":
    for n in sys.argv[1:] or ["dev-p29-vs-p28", "dev-p29-vs-v0", "dev-p31-vs-v0", "dev-p33-vs-v0",
                              "dev-p34-vs-v0", "dev-p35-vs-v0", "dev-p36-vs-v0",
                              "holdout-p31-vs-v0", "holdout-p36-vs-v0"]:
        show(n)
