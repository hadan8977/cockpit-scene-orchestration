import json, sys, collections
from pathlib import Path
import split_analysis as SA

run = sys.argv[1]
rows = [json.loads(l) for l in Path(f"results/{run}/raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
arms = collections.OrderedDict()
for r in rows:
    arms.setdefault(r["variant"], []).append(r)

def und_len(r):
    try:
        return len(json.loads(r["raw_text"]).get("understanding") or "")
    except Exception:
        return None

print("| arm | n | json_valid | schema_valid | pass | intent_ok | name_ok | safety | und chars zh | und chars en | say chars |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for name, rs in arms.items():
    n = len(rs)
    def pct(k): return 100.0*sum(1 for r in rs if r["score"].get(k))/n
    safety = sum(len(r["score"].get("violations") or []) for r in rs)
    uz = [und_len(r) for r in rs if r["lang"]=="zh"]; uz=[x for x in uz if x]
    ue = [und_len(r) for r in rs if r["lang"]=="en"]; ue=[x for x in ue if x]
    says=[]
    for r in rs:
        try: says.append(len(json.loads(r["raw_text"]).get("say") or ""))
        except Exception: pass
    says=[s for s in says if s>0]
    print("| %s | %d | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %d | %.1f | %.1f | %.1f |" % (
        name, n, pct("json_valid"), pct("schema_valid"), pct("pass"), pct("intent_ok"), pct("name_ok"),
        safety, sum(uz)/len(uz) if uz else 0, sum(ue)/len(ue) if ue else 0, sum(says)/len(says) if says else 0))

print()
print("failure split (of non-pass):")
print("| arm | fails | format-only | substantive |")
print("|---|---:|---:|---:|")
for name, rs in arms.items():
    f = [r for r in rs if not r["score"].get("pass")]
    fo = sum(1 for r in f if SA.format_only(r["score"].get("fail_reason")))
    print("| %s | %d | %d | %d |" % (name, len(f), fo, len(f)-fo))

print()
cats = sorted({r["cat"] for r in rows})
print("| category | " + " | ".join(arms) + " |")
print("|---|" + "---:|"*len(arms))
for c in cats:
    cells=[]
    for name, rs in arms.items():
        sub=[r for r in rs if r["cat"]==c]
        cells.append("%.0f%% (%d)"%(100.0*sum(1 for r in sub if r["score"].get("pass"))/len(sub), len(sub)) if sub else "-")
    print("| %s | %s |"%(c, " | ".join(cells)))
