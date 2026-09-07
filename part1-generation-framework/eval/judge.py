#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""体验门评审器（双路里的“机器路”）：用一个评审模型给情绪、模糊、弱意图、记忆、显式创建类输出打分。
维度（各 1 到 5）：贴切（懂了此刻要什么）、分寸（该少则少、不推销不越界）、话术（say 短、引用原词、不说教不追问）、密度（动作数量与元素搭配合适）。
旗标：说教、推销、追问原因、假设关系、复述情绪、功能性动作误用。

用法：
  python3 judge.py --tag smoke-kimi-k27-p3-zh --judge-key kimi-k2.7            # 评一次运行
  python3 judge.py --tag a,b,c --judge-key kimi-k2.7 --compare                  # 多次运行并排
输出：results/<tag>/judge.jsonl、judge_summary.md；--compare 时另写 results/judge-compare-<time>.md
评审模型与被评模型应不同；同一模型自评时结果只作参考并在报告里注明。
"""
import argparse, json, os, sys, re, time, statistics
import concurrent.futures as cf
import run_eval as R

HERE = os.path.dirname(os.path.abspath(__file__))
JUDGE_CATS = ["affect", "vague", "weak", "memory", "explicit", "observe", "clarify"]
DIMS = ["fit", "restraint", "wording", "density"]
DIM_ZH = {"fit": "贴切", "restraint": "分寸", "wording": "话术", "density": "密度"}
FLAGS = ["lecturing", "upselling", "probing", "assumed_relationship", "echoing_emotion", "functional_misuse"]

JUDGE_PROMPT = """你是座舱产品的体验评审。下面是一位用户在车里说的一句话（可能带档案、记忆、状态），以及一个“场景编排模型”给出的布置方案。模型不负责聊天回话，只负责布置环境：光（氛围灯）、声（音乐、音量）、气（香氛）、温（温度、风量、座椅加热通风按摩）、话（say，一句不超过 15 字的话）、供（offer，一个出口：打电话、导航、发消息或无）。

请按四个维度打 1 到 5 分，并给旗标。评分标准：
- 贴切 fit：布置是否对准“此刻这个人需要什么”。5 分是抓住了原话里的关键词并落到对的元素；1 分是答非所问或套模板。
- 分寸 restraint：该少则少。闲聊、抱怨、满意的感叹不应被当成需求；负面记忆和拒绝过的东西不能再出现；行驶中不做大动作。5 分是刚刚好，1 分是推销或越界。
- 话术 wording：say 是否短、自然、引用原词、不说教、不追问原因、不解释自己做了什么、不用“亲爱的”；要安静时应极短或为空。没有 say 且不需要 say 也给 5 分。
- 密度 density：动作数量与元素搭配是否合适。什么都不做有时是满分；四个以上动作几乎总是扣分；同一元素堆两个动作扣分。
旗标（true/false）：lecturing 说教、upselling 推销或多做、probing 追问原因或追问“想谁了”、assumed_relationship 无档案却假设关系、echoing_emotion 复述情绪词、functional_misuse 情绪或舒适目标用了 MAX AC、除雾、ECO 等功能性动作。

只输出 JSON：{"fit":1-5,"restraint":1-5,"wording":1-5,"density":1-5,"flags":{"lecturing":bool,"upselling":bool,"probing":bool,"assumed_relationship":bool,"echoing_emotion":bool,"functional_misuse":bool},"one_line":"一句话评语，不超过 30 字"}

【上下文】
{context}
【用户说】
{input}
【模型的理解句】
{understanding}
【模型的布置】
意图：{intent}；相关度：{relevance}
条件：{conditions}
动作：{actions}
say：{say}
offer：{offer}
记忆建议：{memory}
追问：{clarify}
"""

def load_rows(tag):
    p = os.path.join(HERE, "results", tag, "raw.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def fmt(row):
    ps = (row["score"].get("parsed") or {})
    ctx = ""
    if "\n用户：" in (row["input"] or "") or "\nUser: " in (row["input"] or ""):
        pass
    vals = {"context": row.get("context") or "（无）", "input": row["input"], "understanding": ps.get("understanding") or "（空）",
            "intent": str(ps.get("intent")), "relevance": str(ps.get("relevance")),
            "conditions": json.dumps(ps.get("conditions") or [], ensure_ascii=False), "actions": json.dumps(ps.get("actions") or [], ensure_ascii=False),
            "say": ps.get("say") or "（空）", "offer": json.dumps(ps.get("offer"), ensure_ascii=False), "memory": json.dumps(ps.get("memory") or [], ensure_ascii=False),
            "clarify": ps.get("clarify") or "（无）"}
    t = JUDGE_PROMPT
    for k, v in vals.items():
        t = t.replace("{" + k + "}", str(v))
    return t

def judge_one(cfg, row):
    if not row["score"].get("json_valid"):
        return {"id": row["id"], "lang": row["lang"], "rep": row["rep"], "skipped": "输出不是 JSON"}
    r = R.call_model(cfg, "你是严格但公平的座舱体验评审，只输出 JSON。", fmt(row))
    obj = R.extract_json(r["text"]) if r["text"] else None
    out = {"id": row["id"], "cat": row["cat"], "lang": row["lang"], "rep": row["rep"], "judge_latency": r["latency"], "error": r["error"]}
    if not isinstance(obj, dict):
        out["skipped"] = "评审输出不可解析"; return out
    for d in DIMS:
        try: out[d] = max(1, min(5, int(obj.get(d))))
        except Exception: out[d] = None
    fl = obj.get("flags") or {}
    out["flags"] = {f: bool(fl.get(f)) for f in FLAGS}
    out["one_line"] = str(obj.get("one_line") or "")[:60]
    return out

def summarize(tag, js):
    ok = [j for j in js if all(j.get(d) is not None for d in DIMS)]
    S = {"tag": tag, "n": len(ok), "skipped": len(js) - len(ok)}
    for d in DIMS:
        S[d] = statistics.mean(j[d] for j in ok) if ok else None
    S["overall"] = statistics.mean(sum(j[d] for d in DIMS) / 4 for j in ok) if ok else None
    S["flags"] = {f: sum(1 for j in ok if j["flags"].get(f)) for f in FLAGS}
    S["by_cat"] = {}
    for c in sorted(set(j["cat"] for j in ok)):
        rs = [j for j in ok if j["cat"] == c]
        S["by_cat"][c] = {"n": len(rs), **{d: statistics.mean(j[d] for j in rs) for d in DIMS}}
    S["low"] = sorted([j for j in ok], key=lambda j: sum(j[d] for d in DIMS))[:8]
    return S

def write_summary(tag, S, judge_model):
    L = ["# 体验评审 %s" % tag, "", "评审模型：%s；评了 %d 条，跳过 %d 条（非 JSON 输出）。分数 1 到 5，体验门设计值：四项均值不低于 3.5，且任一项不低于 3.0 [设计值]。" % (judge_model, S["n"], S["skipped"]), "",
         "| 贴切 | 分寸 | 话术 | 密度 | 总均值 |", "|---|---|---|---|---|",
         "| %.2f | %.2f | %.2f | %.2f | %.2f |" % tuple((S[d] or 0) for d in DIMS + ["overall"]), "",
         "旗标次数：" + "、".join("%s %d" % (f, n) for f, n in S["flags"].items()), "", "## 分类别", "", "| 类别 | n | 贴切 | 分寸 | 话术 | 密度 |", "|---|---|---|---|---|---|"]
    for c, v in S["by_cat"].items():
        L.append("| %s | %d | %.2f | %.2f | %.2f | %.2f |" % (c, v["n"], v["fit"], v["restraint"], v["wording"], v["density"]))
    L += ["", "## 最低的几条", ""]
    for j in S["low"]:
        L.append("- %s（%s，%s）贴切 %d 分寸 %d 话术 %d 密度 %d：%s" % (j["id"], j["cat"], j["lang"], j["fit"], j["restraint"], j["wording"], j["density"], j.get("one_line", "")))
    open(os.path.join(HERE, "results", tag, "judge_summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(S, open(os.path.join(HERE, "results", tag, "judge_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\n".join(L[:9]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="一个或多个 results 目录名，逗号分隔")
    ap.add_argument("--judge-key", default="kimi-k2.7")
    ap.add_argument("--cats", default=",".join(JUDGE_CATS))
    ap.add_argument("--rep", type=int, default=0, help="只评第几次重复，-1 为全部")
    ap.add_argument("--lang", default="both")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--force", action="store_true", help="已有 judge.jsonl 也重评")
    ap.add_argument("--resume", action="store_true", default=True, help="默认开：已评且没出错的条目不重评，只补评缺的与出错的（评审也走同一个代理，计入 1200 次 / 5 小时配额）")
    ap.add_argument("--no-resume", dest="resume", action="store_false")
    args = ap.parse_args()
    cfg = {"temperature": 0.0, "max_tokens": 400, "thinking": "off", "timeout": 90, "reasoning_effort": None, "json_mode": True, "response_format": "json_object"}
    cfg.update(R.resolve_model(os.path.join(HERE, "models.json"), args.judge_key))
    if not cfg["api_key"]:
        sys.exit("评审模型缺少 key")
    cats = set(args.cats.split(","))
    summaries = []
    for tag in args.tag.split(","):
        jp = os.path.join(HERE, "results", tag, "judge.jsonl")
        rows = [r for r in load_rows(tag) if r["cat"] in cats and (args.rep < 0 or r["rep"] == args.rep) and (args.lang == "both" or r["lang"] == args.lang)]
        done = []
        if os.path.exists(jp) and not args.force:
            old_js = [json.loads(l) for l in open(jp, encoding="utf-8") if l.strip()]
            if args.resume:
                done = [j for j in old_js if not j.get("error") and not j.get("skipped") and all(j.get(d) is not None for d in DIMS)]
            else:
                done = old_js
        have = set((j["id"], j["lang"], j.get("rep", 0)) for j in done)
        todo = [r for r in rows if (r["id"], r["lang"], r["rep"]) not in have]
        if todo:
            print("评审 %s：已有可用 %d 条，本次补评 %d 条" % (tag, len(done), len(todo)), flush=True)
            with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
                new_js = list(ex.map(lambda r: judge_one(cfg, r), todo))
        else:
            print("评审 %s：已有可用 %d 条，无需补评" % (tag, len(done)), flush=True)
            new_js = []
        js = done + new_js
        js.sort(key=lambda j: (j["id"], j["lang"], j.get("rep", 0)))
        with open(jp, "w", encoding="utf-8") as f:
            for j in js: f.write(json.dumps(j, ensure_ascii=False) + "\n")
        S = summarize(tag, js); summaries.append(S)
        model = json.load(open(os.path.join(HERE, "results", tag, "summary.json"), encoding="utf-8")).get("model")
        S["model"] = model
        note = "（评审模型与被评模型相同，只作参考）" if model == cfg["model"] else ""
        write_summary(tag, S, cfg["model"] + note)
    if args.compare and len(summaries) > 1:
        L = ["# 体验评审并排", "", "| 运行 | 模型 | n | 贴切 | 分寸 | 话术 | 密度 | 总均值 | 说教 | 推销 | 追问 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for S in summaries:
            L.append("| %s | %s | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %d | %d | %d |" % (S["tag"], S["model"], S["n"], S["fit"], S["restraint"], S["wording"], S["density"], S["overall"], S["flags"]["lecturing"], S["flags"]["upselling"], S["flags"]["probing"]))
        p = os.path.join(HERE, "results", "judge-compare-%s.md" % time.strftime("%Y%m%d-%H%M"))
        open(p, "w", encoding="utf-8").write("\n".join(L) + "\n"); print("\n".join(L)); print(p)

if __name__ == "__main__":
    main()
