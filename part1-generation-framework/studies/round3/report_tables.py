"""Every number in delivery/09 comes from here. Offline: reads stored runs, makes no API call.

All runs are scored by ONE scorer (rescore.py, contract v4, capability set r3) so arms produced
before and after the contract edits are comparable. rescore.py reproduces the live scores of
r3_12_p36 and r3_13_p36_holdout exactly, which is why its output is trusted for the earlier runs.
Out-of-scope items (PRD 3.5 单动作不走场景) are excluded everywhere.
"""
import json, collections, statistics
from pathlib import Path

DEV_OOS = set("A01 A05 A09 A14 C05 C09 D02 F12 N01 N05 N10".split())
HO_OOS = set("R3H001 R3H002 R3H003 R3H004 R3H005 R3H007 R3H008 R3H009 R3H022 "
             "R3H039 R3H046 R3H047 R3H048 R3H049 R3H050".split())
OOS = DEV_OOS | HO_OOS
ZH = {"action": "设备命令", "precise": "精确自动化", "vague": "模糊目标", "affect": "情绪回应",
      "weak": "状态表达", "clarify": "该追问", "robust": "误转写", "explicit": "显式建场景",
      "attack": "注入越权", "memory": "记忆建议", "observe": "观察候选"}


def load(run):
    p = Path(f"results/{run}/raw.v4.jsonl")
    if not p.exists():
        p = Path(f"results/{run}/raw.jsonl")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def pick(rows, arm):
    return [r for r in rows if r["variant"] == arm and r["id"] not in OOS]


def stats(rows, arm):
    s = pick(rows, arm); n = len(s)
    if not n: return None
    g = lambda k: sum(1 for r in s if r["score"].get(k)) / n
    P = lambda r: (r["score"].get("parsed") or {})
    lat = sorted(r["latency"] for r in s if r.get("latency"))
    tu = sorted(r["t_und"] for r in s if r.get("t_und"))
    zh = [len(P(r).get("understanding") or "") for r in s if r["lang"] == "zh" and P(r)]
    en = [len(P(r).get("understanding") or "") for r in s if r["lang"] == "en" and P(r)]
    return dict(n=n, json=g("json_valid"), schema=g("schema_valid"), task=g("pass"),
                intent=g("intent_ok"), name=g("name_ok"), lang=g("language_ok"),
                sv=sum(any("安全违规" in v for v in r["score"].get("violations", [])) for r in s),
                p50=lat[len(lat)//2], p95=lat[int(len(lat)*0.95)],
                und50=tu[len(tu)//2] if tu else 0,
                zh=sum(zh)/len(zh) if zh else 0, en=sum(en)/len(en) if en else 0,
                say=sum(1 for r in s if P(r).get("say")) / n)


def paired(rows_a, arm_a, rows_b, arm_b):
    A = {(r["id"], r["lang"]): bool(r["score"].get("pass")) for r in pick(rows_a, arm_a)}
    B = {(r["id"], r["lang"]): bool(r["score"].get("pass")) for r in pick(rows_b, arm_b)}
    k = set(A) & set(B)
    return len(k), sum(1 for x in k if A[x] and not B[x]), sum(1 for x in k if B[x] and not A[x])


def bycat(rows, arm):
    d = collections.defaultdict(lambda: [0, 0])
    for r in pick(rows, arm):
        d[r["cat"]][1] += 1
        d[r["cat"]][0] += 1 if r["score"].get("pass") else 0
    return d


def fail_reasons(rows, arm, top=8):
    c = collections.Counter()
    for r in pick(rows, arm):
        if r["score"].get("pass"): continue
        fr = (r["score"].get("fail_reason") or "").split(";")[0].strip()
        c[fr.split(":")[0][:40] or "(空)"] += 1
    return c.most_common(top)


LINEAGE = [("p28", "r3_02_screen_full"), ("p29", "r3_03_p29"), ("p31", "r3_05_equal"),
           ("p32", "r3_07_p32"), ("p33", "r3_08_p33"), ("p34", "r3_09_p34"),
           ("p35", "r3_10_p35"), ("p36", "r3_12_p36"),
           ("v3_r3", "r3_05_equal"), ("v0_r3", "r3_05_equal"), ("v0_c4", "r3_02_screen_full")]

if __name__ == "__main__":
    print("### 第三轮谱系（开发集在范围内 123 题 × 中英）")
    h = f'{"版本":8s} {"n":>4s} {"解析":>7s} {"合结构":>7s} {"任务对":>7s} {"意图":>7s} {"安全":>4s} {"中理解":>6s} {"英理解":>6s} {"开口":>5s} {"p50":>6s}'
    print(h); print("-" * len(h))
    for arm, run in LINEAGE:
        s = stats(load(run), arm)
        if not s: continue
        print(f'{arm:8s} {s["n"]:4d} {s["json"]*100:6.1f}% {s["schema"]*100:6.1f}% {s["task"]*100:6.1f}% '
              f'{s["intent"]*100:6.1f}% {s["sv"]:4d} {s["zh"]:6.1f} {s["en"]:6.1f} {s["say"]*100:4.0f}% {s["p50"]:6.3f}')

    for label, (rc, ac, rb) in (("开发集在范围内 123 题", ("r3_12_p36", "p36", "r3_05_equal")),
                                ("留出集在范围内 50 题", ("r3_13_p36_holdout", "p36", "r3_06_holdout"))):
        C, B = load(rc), load(rb)
        print(f"\n### {label}")
        print(f'{"":18s} {"n":>4s} {"解析":>7s} {"合结构":>7s} {"任务对":>7s} {"意图":>7s} {"安全":>4s} {"p50":>6s} {"p95":>6s} {"理解句p50":>8s}')
        for nm, rows, arm in ((f"{ac} 定版", C, ac), ("v3_r3 一轮基线", B, "v3_r3"), ("v0_r3 同事原版", B, "v0_r3")):
            s = stats(rows, arm)
            print(f'{nm:18s} {s["n"]:4d} {s["json"]*100:6.1f}% {s["schema"]*100:6.1f}% {s["task"]*100:6.1f}% '
                  f'{s["intent"]*100:6.1f}% {s["sv"]:4d} {s["p50"]:6.3f} {s["p95"]:6.3f} {s["und50"]:8.3f}')
        for arm in ("v3_r3", "v0_r3"):
            k, w, l = paired(C, ac, B, arm)
            print(f'   题级配对 {ac} 对 {arm}：共 {k} 对，{ac} 赢 {w}，{arm} 赢 {l}')
        a, b, c = bycat(C, ac), bycat(B, "v3_r3"), bycat(B, "v0_r3")
        print(f'   {"类别":14s} {"题":>3s} {ac:>8s} {"v3_r3":>8s} {"v0_r3":>8s}')
        for k in sorted(a, key=lambda x: -a[x][0]/a[x][1]):
            f = lambda d: f'{d[k][0]/d[k][1]*100:7.1f}%' if k in d else "      -"
            print(f'   {ZH.get(k,k):14s} {a[k][1]//2:3d} {f(a)} {f(b)} {f(c)}')
        print(f'   {ac} 失败首因：', fail_reasons(C, ac))
        print(f'   v0_r3 失败首因：', fail_reasons(B, "v0_r3"))
