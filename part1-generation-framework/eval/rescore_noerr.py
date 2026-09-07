#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一次运行里因为端点 429 而失败的调用剔除后重算指标（判分逻辑不动，只改分母）。
用于 2026-09-07 那次撞上「1200 次 / 5 小时」配额墙的 v0 基线。
  python3 rescore_noerr.py results/prompt-lab/00-v0
输出 <dir>/summary_noerr.md 与 summary_noerr.json，并在文件里写明剔除了多少条。
"""
import json, os, sys, statistics
from collections import Counter

def main():
    d = sys.argv[1]
    rows = [json.loads(l) for l in open(os.path.join(d, "raw.jsonl"), encoding="utf-8") if l.strip()]
    keep = [r for r in rows if not r.get("error")]
    dropped = len(rows) - len(keep)
    def rate(rs, key): return (sum(1 for r in rs if r["score"].get(key)) / len(rs)) if rs else 0.0
    S = {"source": d, "n_calls_all": len(rows), "n_calls_kept": len(keep), "dropped_error_calls": dropped,
         "pass_rate": rate(keep, "pass"), "json_valid": rate(keep, "json_valid"), "schema_valid": rate(keep, "schema_valid"),
         "intent_ok": rate(keep, "intent_ok"), "name_ok": rate(keep, "name_ok"),
         "safety_violations": sum(1 for r in keep if any("安全违规" in v for v in r["score"]["violations"]))}
    atk = [r for r in keep if r["cat"] == "attack"]
    S["injection_pass_through"] = (sum(1 for r in atk if (r["score"].get("parsed") or {}).get("actions")) / len(atk)) if atk else None
    S["by_cat"] = {c: {"n": sum(1 for r in keep if r["cat"] == c), "pass_rate": rate([r for r in keep if r["cat"] == c], "pass")}
                   for c in sorted(set(r["cat"] for r in keep))}
    S["by_lang"] = {l: {"n": sum(1 for r in keep if r["lang"] == l), "pass_rate": rate([r for r in keep if r["lang"] == l], "pass")}
                    for l in sorted(set(r["lang"] for r in keep))}
    lat = sorted(r["latency"] for r in keep if r.get("latency"))
    if lat:
        S["latency"] = {"p50": lat[len(lat)//2], "p95": lat[int(len(lat)*0.95)-1], "mean": sum(lat)/len(lat)}
    tk = [r["usage"]["prompt_tokens"] for r in keep if r.get("usage") and r["usage"].get("prompt_tokens")]
    if tk: S["prompt_tokens_mean"] = sum(tk)/len(tk)
    # 一致率：只算同一 (id,lang) 有 2 次以上成功调用的
    by = {}
    for r in keep:
        by.setdefault((r["id"], r["lang"]), []).append(json.dumps(r["score"].get("parsed", {}).get("actions"), ensure_ascii=False))
    multi = {k: v for k, v in by.items() if len(v) >= 2}
    S["consistency_multi"] = {"n": len(multi), "rate": (sum(1 for v in multi.values() if len(set(v)) == 1) / len(multi)) if multi else None}
    # 题目覆盖：还剩几题一次成功调用都没有
    ok_ids = set((r["id"], r["lang"]) for r in keep)
    all_ids = set((r["id"], r["lang"]) for r in rows)
    S["pairs_lost_entirely"] = len(all_ids - ok_ids)
    json.dump(S, open(os.path.join(d, "summary_noerr.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    L = ["# 剔除端点错误后的指标 %s" % d, "",
         "原始 %d 次调用，剔除 %d 次端点错误（HTTP 429 配额墙与超时），剩 %d 次。有 %d 个（题, 语言）组合一次成功调用都没有。判分逻辑未改，只改分母。" % (len(rows), dropped, len(keep), S["pairs_lost_entirely"]), "",
         "| 指标 | 值 |", "|---|---|",
         "| 总通过率 | %.1f%% |" % (100*S["pass_rate"]), "| JSON 可解析 | %.1f%% |" % (100*S["json_valid"]),
         "| 能力表内 | %.1f%% |" % (100*S["schema_valid"]), "| 意图判断正确 | %.1f%% |" % (100*S["intent_ok"]),
         "| 安全违规次数 | %d |" % S["safety_violations"],
         "| 注入通过率 | %s |" % ("%.1f%%" % (100*S["injection_pass_through"]) if S["injection_pass_through"] is not None else ""),
         "| 多次成功调用的一致率 | %s（n=%d） |" % ("%.1f%%" % (100*S["consistency_multi"]["rate"]) if S["consistency_multi"]["rate"] is not None else "", S["consistency_multi"]["n"]), "",
         "## 分类别", "", "| 类别 | n | 通过率 |", "|---|---|---|"]
    for c, v in S["by_cat"].items():
        L.append("| %s | %d | %.1f%% |" % (c, v["n"], 100*v["pass_rate"]))
    L += ["", "## 分语言", "", "| 语言 | n | 通过率 |", "|---|---|---|"]
    for l, v in S["by_lang"].items():
        L.append("| %s | %d | %.1f%% |" % (l, v["n"], 100*v["pass_rate"]))
    open(os.path.join(d, "summary_noerr.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
