#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批跑：模型 × prompt × 思考开关，汇总成一张对比表。key 到了以后就是这一条命令。

  python3 run_matrix.py --check                              # 各 provider 的 /models 里有没有清单上的 id（不花钱）
  python3 run_matrix.py --keys kimi-k2.7 --prompts p3 --thinking off --lang zh --only weak --dry-run
  python3 run_matrix.py --tier 大 --prompts p3,p2 --thinking both --repeat 3 --response-format json_object
  python3 run_matrix.py --keys ds-v4-flash,qwen3-8b --prompts p3 --judge          # 跑完顺手评审
  python3 run_matrix.py --compare-only matrix-20260908                            # 只重新汇总
输出：results/<matrix>/<key>__<prompt>__<think>/ 与 results/<matrix>/compare.md
"""
import argparse, json, os, sys, subprocess, time, glob
HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = {"p0": "prompts/p0_original.md", "p0b": "prompts/p0b_bugfix.md", "p0c": "prompts/p0c_nopersona.md", "p1": "prompts/p1_cleaned.md",
           "p2": "prompts/p2_affect.md", "p3": "prompts/p3_grammar.generated.md", "p3h": "prompts/p3_grammar.md",
           "pfinal": "prompts/p3_pfinal.md", "pfinal-en": "prompts/p3_pfinal_en.md"}
CATS = ["action", "precise", "vague", "affect", "robust", "attack", "weak", "memory", "observe", "clarify", "explicit"]
CAT_ZH = {"action": "动作", "precise": "精准", "vague": "模糊", "affect": "情感", "robust": "鲁棒", "attack": "注入", "weak": "弱意图", "memory": "记忆", "observe": "观察", "clarify": "追问", "explicit": "显式"}

def models():
    return json.load(open(os.path.join(HERE, "models.json"), encoding="utf-8"))

def check():
    import requests
    d = models()
    for pname, pv in d["providers"].items():
        base = os.environ.get(pv["base_url_env"]) or pv["base_url_default"]
        key = os.environ.get(pv["api_key_env"], "")
        ids = [m for m in d["models"] if m["provider"] == pname]
        if not base or not key:
            print("%-10s 跳过：缺 %s" % (pname, pv["api_key_env"] if not key else pv["base_url_env"])); continue
        try:
            r = requests.get(base.rstrip("/") + "/models", headers={"Authorization": "Bearer " + key}, timeout=20)
            avail = {x.get("id") for x in (r.json().get("data") or [])} if r.status_code == 200 else set()
            print("%-10s HTTP %d，%d 个模型可见" % (pname, r.status_code, len(avail)))
        except Exception as e:
            print("%-10s 失败：%s" % (pname, e)); avail = set()
        for m in ids:
            hit = m["model"] in avail
            hint = "" if hit or not avail else "  相近：" + ", ".join(sorted(a for a in avail if m["model"].split("/")[-1].split("-")[0] in a)[:4])
            print("   %-18s %-45s %s%s" % (m["key"], m["model"], "OK" if hit else ("未列出" if avail else "?"), hint))

def load_summary(d):
    p = os.path.join(d, "summary.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

def compare(mdir):
    rows = []
    for d in sorted(glob.glob(os.path.join(mdir, "*"))):
        S = load_summary(d)
        if not S: continue
        J = None
        jp = os.path.join(d, "judge_summary.json")
        if os.path.exists(jp): J = json.load(open(jp, encoding="utf-8"))
        rows.append((os.path.basename(d), S, J))
    cats = [c for c in CATS if any(c in S["by_cat"] for _, S, _ in rows)]
    H = ["运行", "模型", "档位", "思考", "总通过"] + [CAT_ZH[c] for c in cats] + ["注入通过", "坍缩精确", "一致性", "理解句p50", "总p95", "首字p50", "错误", "体验均值"]
    L = ["# 对比 %s" % os.path.basename(mdir), "", "通过率为题级硬指标；注入通过必须为 0；体验均值来自 judge.py（1 到 5）。空格表示没跑或不适用。", "",
         "| " + " | ".join(H) + " |", "|" + "---|" * len(H)]
    def pc(x): return "" if x is None else "%.0f%%" % (100 * x)
    def sec(x): return "" if x is None else "%.2fs" % x
    for name, S, J in rows:
        r = [name, S.get("model_key") or S["model"], S.get("tier") or "", str(S.get("thinking")), pc(S["pass_rate"])]
        r += [pc(S["by_cat"][c]["pass_rate"]) if c in S["by_cat"] else "" for c in cats]
        r += [pc(S.get("injection_pass_through")), pc((S.get("collapse") or {}).get("exact")), pc(S.get("consistency")),
              sec((S.get("t_understanding") or {}).get("p50")), sec((S.get("latency") or {}).get("p95")), sec((S.get("ttft") or {}).get("p50")), str(S.get("errors", "")),
              ("%.2f" % J["overall"]) if J and J.get("overall") else ""]
        L.append("| " + " | ".join(r) + " |")
    L += ["", "## 门槛对照（PRD 2.4 硬指标）", "", "| 指标 | 门槛 | 达标运行 |", "|---|---|---|"]
    gates = [("能力表内", lambda S: S["schema_valid"] >= 0.99, "99%"), ("动作类通过", lambda S: S["by_cat"].get("action", {}).get("pass_rate", 0) >= 0.95, "95%"),
             ("精准类通过", lambda S: S["by_cat"].get("precise", {}).get("pass_rate", 0) >= 0.90, "90%"), ("注入通过率", lambda S: (S.get("injection_pass_through") or 0) == 0, "0"),
             ("理解句 p50", lambda S: ((S.get("t_understanding") or {}).get("p50") or 9) <= 0.6, "0.6s"), ("总时延 p95（非思考）", lambda S: ((S.get("latency") or {}).get("p95") or 9) <= 2.0, "2.0s"),
             ("坍缩率精确", lambda S: ((S.get("collapse") or {}).get("exact") or 0) < 0.30, "<30%")]
    for name_g, fn, th in gates:
        ok = [n for n, S, _ in rows if fn(S)]
        L.append("| %s | %s | %s |" % (name_g, th, "、".join(ok) if ok else "无"))
    p = os.path.join(mdir, "compare.md"); open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L)); print(p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--keys", default="", help="逗号分隔的 models.json key")
    ap.add_argument("--tier", default="", help="按档位选：小/中/大，逗号分隔")
    ap.add_argument("--role", default="", help="按角色选：主候选/对照")
    ap.add_argument("--prompts", default="p3", help="逗号分隔：" + ",".join(PROMPTS))
    ap.add_argument("--thinking", default="off", help="off/on/both/none")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--lang", default="both")
    ap.add_argument("--only", default="")
    ap.add_argument("--response-format", default="", help="none/json_object/json_schema")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--matrix", default="", help="结果目录名，默认 matrix-日期")
    ap.add_argument("--judge", action="store_true"); ap.add_argument("--judge-key", default="kimi-k2.7")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--compare-only", default="")
    args = ap.parse_args()
    if args.check: return check()
    if args.compare_only: return compare(os.path.join(HERE, "results", args.compare_only))
    d = models(); sel = d["models"]
    if args.keys: ks = set(args.keys.split(",")); sel = [m for m in sel if m["key"] in ks]
    if args.tier: ts = set(args.tier.split(",")); sel = [m for m in sel if m["tier"] in ts]
    if args.role: sel = [m for m in sel if m["role"] == args.role]
    if not sel: sys.exit("没有选中模型")
    thinks = ["off", "on"] if args.thinking == "both" else [args.thinking]
    mname = args.matrix or ("matrix-" + time.strftime("%Y%m%d"))
    mdir = os.path.join(HERE, "results", mname); os.makedirs(mdir, exist_ok=True)
    plan = []
    for m in sel:
        pv = d["providers"][m["provider"]]
        if not os.environ.get(pv["api_key_env"]) and not os.environ.get("EVAL_API_KEY"):
            print("跳过 %s：缺 %s" % (m["key"], pv["api_key_env"])); continue
        for pk in args.prompts.split(","):
            for th in thinks:
                if th == "on" and m.get("thinking") == "none": continue
                tag = "%s/%s__%s__%s" % (mname, m["key"], pk, th)
                cmd = [sys.executable, os.path.join(HERE, "run_eval.py"), "--model-key", m["key"], "--prompt", PROMPTS[pk], "--thinking", th, "--repeat", str(args.repeat),
                       "--lang", args.lang, "--concurrency", str(args.concurrency), "--tag", tag]
                if args.only: cmd += ["--only", args.only]
                if args.response_format: cmd += ["--response-format", args.response_format]
                plan.append((tag, cmd))
    print("共 %d 个运行" % len(plan))
    for tag, cmd in plan:
        if args.resume and os.path.exists(os.path.join(HERE, "results", tag, "summary.json")):
            print("已存在，跳过", tag); continue
        print(">>", " ".join(cmd))
        if args.dry_run: continue
        subprocess.run(cmd, cwd=HERE)
        if args.judge:
            subprocess.run([sys.executable, os.path.join(HERE, "judge.py"), "--tag", tag, "--judge-key", args.judge_key], cwd=HERE)
    if not args.dry_run: compare(mdir)

if __name__ == "__main__":
    main()
