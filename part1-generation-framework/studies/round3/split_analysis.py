"""Apply the AMENDMENT-13 format-versus-substance split to any run. Definition fixed before first use."""
import argparse
import collections
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMAT_PREFIXES = ("契约 name", "契约 understanding", "契约 say", "规划中或提议动作缺少能力名警告")


def format_only(reason):
    parts = [p.strip() for p in (reason or "").split(";") if p.strip()]
    return bool(parts) and all(any(p.startswith(f) for f in FORMAT_PREFIXES) for p in parts)


def analyse(run):
    rows = [json.loads(l) for l in (HERE / "results" / run / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = {}
    for variant in sorted({r["variant"] for r in rows}):
        subset = [r for r in rows if r["variant"] == variant]
        n = len(subset)
        usable = sum(bool(r["score"].get("usable")) for r in subset)
        fmt = sum(not r["score"].get("usable") and format_only(r["score"].get("fail_reason")) for r in subset)
        sub = n - usable - fmt
        out[variant] = {
            "n": n,
            "usable": usable / n,
            "fail_format_only": fmt / n,
            "fail_substantive": sub / n,
            "task_quality_excluding_format": (usable + fmt) / n,
            "intent_ok": sum(bool(r["score"].get("intent_ok")) for r in subset) / n,
            "safety_violations": sum(any("安全违规" in v for v in r["score"].get("violations", [])) for r in subset),
            "p50": statistics.median([r["latency"] for r in subset if not r["error"]]),
        }
    return out


def paired(run, candidate, baseline, metric="task_quality"):
    rows = [json.loads(l) for l in (HERE / "results" / run / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by = collections.defaultdict(dict)
    for r in rows:
        ok = bool(r["score"].get("usable")) or format_only(r["score"].get("fail_reason"))
        by[(r["id"], r["lang"])][r["variant"]] = ok if metric == "task_quality" else bool(r["score"].get("usable"))
    pairs = [(k, by[k][candidate] - by[k][baseline]) for k in by if candidate in by[k] and baseline in by[k]]
    if not pairs:
        return None
    per_item = collections.defaultdict(list)
    for (item, _lang), d in pairs:
        per_item[item].append(d)
    means = [statistics.mean(v) for v in per_item.values()]
    return {"pairs": len(pairs), "items": len(means), "delta": statistics.mean(means),
            "candidate_better": sum(d > 0 for _, d in pairs), "baseline_better": sum(d < 0 for _, d in pairs)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--pair", nargs=2, metavar=("CANDIDATE", "BASELINE"))
    a = ap.parse_args()
    res = analyse(a.run)
    print(f"{'臂':16s} {'n':>4} {'可用':>7} {'仅格式失败':>9} {'实质失败':>8} {'任务口径':>8} {'意图':>7} {'安全':>4} {'p50':>6}")
    for k, v in res.items():
        print(f"{k:16s} {v['n']:4d} {v['usable']:6.1%} {v['fail_format_only']:8.1%} {v['fail_substantive']:7.1%} "
              f"{v['task_quality_excluding_format']:7.1%} {v['intent_ok']:6.1%} {v['safety_violations']:4d} {v['p50']:6.3f}")
    if a.pair:
        for metric in ("usable", "task_quality"):
            p = paired(a.run, a.pair[0], a.pair[1], metric)
            if p:
                print(f"\n题级配对 [{metric}] {a.pair[0]} 减 {a.pair[1]}：{p['items']} 题 {p['pairs']} 对，"
                      f"均值 {p['delta']:+.4f}，候选赢 {p['candidate_better']} 输 {p['baseline_better']}")
