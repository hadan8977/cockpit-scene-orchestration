#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""体验门盲评打包（双路里的“人工路”）。
把若干次运行（不同模型或 prompt）在同一批句子上的输出匿名成 A/B/C…，生成一张可以直接打分的表；打完分再汇总回模型。

  python3 blind_pack.py build --tags matrix-x/ds__p3__off,matrix-x/qwen3-8b__p3__off --out blind/0908            # 全量盲评表（机器路 judge 也用同一批句子）
  python3 blind_pack.py build --tags ... --out blind/0908 --sample 12 --seed 7                                     # 抽 12 句给用户评
  python3 blind_pack.py score --out blind/0908 --ratings blind/0908/ratings.csv                                    # 汇总
盲评句集在 blind_set.json：36 句，情绪 10、模糊 4、弱意图 8、记忆 4、显式创建 6、追问 2、鲁棒 2，中英各一版。
评分四项各 1 到 5：贴切、分寸、话术、密度；另选一个“首选”。ratings.csv 列：sid,cand,fit,restraint,wording,density,preferred
"""
import argparse, json, os, sys, random, csv, statistics
HERE = os.path.dirname(os.path.abspath(__file__))
BLIND = json.load(open(os.path.join(HERE, "blind_set.json"), encoding="utf-8"))

def rows_of(tag):
    p = os.path.join(HERE, "results", tag, "raw.jsonl")
    return {(r["id"], r["lang"]): r for r in (json.loads(l) for l in open(p, encoding="utf-8") if l.strip()) if r["rep"] == 0}

def chips(ps):
    acts = ps.get("actions") or []
    conds = ps.get("conditions") or []
    a = "、".join("%s=%s" % (p, v) for p, v in acts) or "（不动任何东西）"
    c = "、".join("%s %s %s" % (p, op or "==", v) for p, op, v in conds)
    return a, c

def build(args):
    tags = args.tags.split(","); out = os.path.join(HERE, args.out); os.makedirs(out, exist_ok=True)
    data = {t: rows_of(t) for t in tags}
    sids = [b["id"] for b in BLIND["items"]]
    rnd = random.Random(args.seed)
    if args.sample: sids = rnd.sample(sids, min(args.sample, len(sids)))
    langs = ["zh", "en"] if args.lang == "both" else [args.lang]
    key = {}; L = ["# 盲评表 %s" % args.out, "", "每句下面有若干候选（顺序随机，来自不同模型或 prompt）。四项各打 1 到 5，再勾一个首选。评分定义见测试计划第 5 节。", "",
                   "填到 ratings.csv：sid,cand,fit,restraint,wording,density,preferred（首选填 1 否则 0）", ""]
    csv_rows = []
    for sid in sids:
        for lang in langs:
            b = next(x for x in BLIND["items"] if x["id"] == sid)
            first = None
            for t in tags:
                r = data[t].get((sid, lang))
                if r: first = r; break
            if not first: continue
            skey = "%s-%s" % (sid, lang)
            L += ["## %s" % skey, "", "上下文：%s" % (first.get("context") or first["input"].split("\n用户：")[0] if "\n用户：" in first["input"] else "（无）"), "", "用户说：**%s**" % (first["input"].split("\n用户：")[-1].split("\nUser: ")[-1]), "", "考察：%s" % b.get("tests", first.get("tests", "")), ""]
            cands = [(t, data[t].get((sid, lang))) for t in tags if data[t].get((sid, lang))]
            rnd.shuffle(cands)
            for i, (t, r) in enumerate(cands):
                letter = chr(ord("A") + i); key[skey + "/" + letter] = t
                ps = r["score"].get("parsed") or {}
                a, c = chips(ps)
                L += ["**%s**  理解句：%s" % (letter, ps.get("understanding") or "（空）"), "", "  条件：%s" % (c or "无"), "  动作：%s" % a, "  说：%s　　出口：%s　　记忆：%s　　追问：%s" % (ps.get("say") or "（不说）", json.dumps(ps.get("offer"), ensure_ascii=False), json.dumps(ps.get("memory") or [], ensure_ascii=False), ps.get("clarify") or "无"), ""]
                csv_rows.append([skey, letter, "", "", "", "", ""])
            L += ["贴切 ／ 分寸 ／ 话术 ／ 密度 ／ 首选：", ""]
    open(os.path.join(out, "sheet.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"tags": tags, "key": key, "sample": sids, "langs": langs}, open(os.path.join(out, "key.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(out, "ratings.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["sid", "cand", "fit", "restraint", "wording", "density", "preferred"]); w.writerows(csv_rows)
    print("盲评表：", os.path.join(out, "sheet.md"), "；候选数", len(csv_rows), "；答案在 key.json，评完再看")

def score(args):
    out = os.path.join(HERE, args.out); key = json.load(open(os.path.join(out, "key.json"), encoding="utf-8"))["key"]
    agg = {}
    for row in csv.DictReader(open(args.ratings, encoding="utf-8")):
        if not row.get("fit"): continue
        t = key.get(row["sid"] + "/" + row["cand"])
        if not t: continue
        a = agg.setdefault(t, {"fit": [], "restraint": [], "wording": [], "density": [], "preferred": 0, "n": 0})
        for d in ("fit", "restraint", "wording", "density"): a[d].append(float(row[d]))
        a["preferred"] += int(row.get("preferred") or 0); a["n"] += 1
    L = ["# 盲评汇总 %s" % args.out, "", "| 运行 | n | 贴切 | 分寸 | 话术 | 密度 | 总均值 | 首选次数 |", "|---|---|---|---|---|---|---|---|"]
    for t, a in sorted(agg.items(), key=lambda kv: -statistics.mean(sum(kv[1][d]) / len(kv[1][d]) for d in ("fit", "restraint", "wording", "density"))):
        m = [statistics.mean(a[d]) for d in ("fit", "restraint", "wording", "density")]
        L.append("| %s | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %d |" % (t, a["n"], *m, statistics.mean(m), a["preferred"]))
    open(os.path.join(out, "blind_summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n"); print("\n".join(L))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["build", "score"])
    ap.add_argument("--tags", default=""); ap.add_argument("--out", default="blind/latest"); ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--lang", default="zh"); ap.add_argument("--ratings", default="")
    a = ap.parse_args(); build(a) if a.cmd == "build" else score(a)
