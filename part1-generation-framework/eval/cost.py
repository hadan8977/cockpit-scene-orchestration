#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""费用记账：DeepSeek 官网端点按 token 计费，账户余额是硬约束。
  python3 cost.py                      # 查余额并追加一行到 logs/cost_ledger.txt
  python3 cost.py --estimate <tag>     # 按某次运行的 usage 估算它花了多少（含前缀缓存命中拆分）
价目按 2026 年 deepseek-v4-flash 的公开价目填在 PRICE 里，命中缓存的输入便宜一个数量级；
真正的口径是余额差，估算只用来提前判断一次运行跑不跑得起。
"""
import argparse, json, os, subprocess, glob
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
# 元 / 百万 token
PRICE = {"cache_hit_in": 0.1, "cache_miss_in": 1.0, "out": 2.0}

def balance():
    key = os.environ.get("DEEPSEEK_OFFICIAL_API_KEY", "")
    if not key: return None
    out = subprocess.run(["curl", "-s", "https://api.deepseek.com/user/balance", "-H", "Authorization: Bearer " + key],
                         capture_output=True, text=True).stdout
    try: return json.loads(out)["balance_infos"][0]["total_balance"]
    except Exception: return None

def estimate(tag):
    p = os.path.join(HERE, "results", tag, "raw.jsonl")
    hit = miss = out = n = 0
    for l in open(p, encoding="utf-8"):
        if not l.strip(): continue
        r = json.loads(l); u = r.get("usage") or {}
        if not u: continue
        n += 1
        hit += u.get("prompt_cache_hit_tokens") or (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        miss += u.get("prompt_cache_miss_tokens") or 0
        out += u.get("completion_tokens") or 0
    yuan = hit/1e6*PRICE["cache_hit_in"] + miss/1e6*PRICE["cache_miss_in"] + out/1e6*PRICE["out"]
    print("%s：%d 次有 usage 的调用，缓存命中输入 %d、未命中输入 %d、输出 %d token，按价目估算 %.3f 元（%.4f 元/次）"
          % (tag, n, hit, miss, out, yuan, yuan/max(n,1)))
    return yuan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    if a.estimate:
        estimate(a.estimate); return
    b = balance()
    line = "%s balance %s %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), b, a.note)
    with open(os.path.join(HERE, "logs", "cost_ledger.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)

if __name__ == "__main__":
    main()
