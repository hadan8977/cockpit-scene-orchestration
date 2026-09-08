"""Round-three lineage table over the in-scope development set. Offline, no API calls."""
import json, collections, sys
from pathlib import Path

DEV_OOS = set("A01 A05 A09 A14 C05 C09 D02 F12 N01 N05 N10".split())
HO_OOS = set("R3H001 R3H002 R3H003 R3H004 R3H005 R3H007 R3H008 R3H009 R3H022 R3H039 R3H046 R3H047 R3H048 R3H049 R3H050".split())
OOS = DEV_OOS | HO_OOS

def load(run, fn="raw.jsonl"):
    p = Path(f"results/{run}/{fn}")
    if not p.exists():
        p = Path(f"results/{run}/raw.jsonl")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def stats(rows, arm):
    sel = [r for r in rows if r["variant"] == arm and r["id"] not in OOS]
    n = len(sel)
    if not n: return None
    g = lambda k: sum(1 for r in sel if r.get("score", {}).get(k)) / n
    sv = sum(any("安全违规" in v for v in r["score"].get("violations", [])) for r in sel)
    P = lambda r: (r.get("score") or {}).get("parsed") or {}
    zh = [len(P(r).get("understanding") or "") for r in sel if r["lang"] == "zh" and P(r)]
    en = [len(P(r).get("understanding") or "") for r in sel if r["lang"] == "en" and P(r)]
    say = sum(1 for r in sel if P(r).get("say")) / n
    lat = sorted(r["latency"] for r in sel if r.get("latency"))
    return dict(n=n, json=g("json_valid"), schema=g("schema_valid"), task=g("pass"),
                intent=g("intent_ok"), sv=sv,
                zh=sum(zh)/len(zh) if zh else 0, en=sum(en)/len(en) if en else 0,
                say=say, p50=lat[len(lat)//2] if lat else 0)

if __name__ == "__main__":
    RUNS = [("r3_02_screen_full","p28"),("r3_03_p29","p29"),("r3_05_equal","p31"),
            ("r3_07_p32","p32"),("r3_08_p33","p33"),("r3_09_p34","p34"),
            ("r3_10_p35","p35"),("r3_12_p36","p36"),
            ("r3_05_equal","v3_r3"),("r3_05_equal","v0_r3"),
            ("r3_02_screen_full","v0_c4")]
    hdr = f'{"版本":8s} {"n":>4s} {"解析":>7s} {"合结构":>7s} {"任务对":>7s} {"意图":>7s} {"安全":>4s} {"中理解":>6s} {"英理解":>6s} {"开口":>6s} {"p50":>6s}'
    print(hdr); print("-"*len(hdr))
    for run, arm in RUNS:
        try:
            s = stats(load(run, "raw.v4.jsonl"), arm)
        except Exception:
            s = stats(load(run), arm)
        if not s: print(f"{arm:8s} (无)"); continue
        print(f'{arm:8s} {s["n"]:4d} {s["json"]*100:6.1f}% {s["schema"]*100:6.1f}% {s["task"]*100:6.1f}% '
              f'{s["intent"]*100:6.1f}% {s["sv"]:4d} {s["zh"]:6.1f} {s["en"]:6.1f} {s["say"]*100:5.0f}% {s["p50"]:6.3f}')
