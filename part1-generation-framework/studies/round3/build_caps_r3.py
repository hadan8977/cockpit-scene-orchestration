"""Round-three capability table.

Inclusion rule chosen by the user: any row carrying strikethrough in the source workbook is out,
regardless of what UX情况 says. Everything else is in and is treated as EQUAL — no maturity tiers.
Three team-proposed capabilities that are not in the workbook (天气 / 行程事件 / 音乐播放) are kept and
labelled as such, so the report can separate them from what the source table actually authorises.
"""
import json, hashlib, sys
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "eval"
XLSX = ROOT / "notes" / "inputs" / "座舱原子能力-最新.xlsx"

# --- 1. read the strikethrough facts straight from the workbook
struck_rows, live_rows = [], []
wb = openpyxl.load_workbook(XLSX)
for sheet, kind in (("当满足条件", "cond"), ("就执行", "act")):
    ws = wb[sheet]; hdr = [c.value for c in ws[1]]
    i_ux = hdr.index("UX情况"); i1 = hdr.index("一级能力")
    i2 = [k for k, h in enumerate(hdr) if h and h.strip() == "二级能力"][0]
    i3 = hdr.index("三级能力")
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row]
        if not any(v is not None and str(v).strip() for v in vals): continue
        rec = {"kind": kind, "row": row[0].row, "ux": str(vals[i_ux] or "").strip(),
               "l1": str(vals[i1] or "").strip().split("\n")[0],
               "l2": str(vals[i2] or "").strip().split("\n")[0],
               "l3": str(vals[i3] or "").strip().split("\n")[0]}
        (struck_rows if any(c.font and c.font.strike for c in row if c.value is not None) else live_rows).append(rec)

# --- 2. what the literal rule removes, expressed against the harness vocabulary
DROP_ACTIONS = ["左前门", "右前门", "左后门", "右后门"]          # struck in 就执行, still live in 当满足条件
DROP_ACT_VALUES = {"主驾座椅按摩模式": ["波浪", "猫步", "蛇形", "肩部", "腰部"],
                   "副驾座椅按摩模式": ["波浪", "猫步", "蛇形", "肩部", "腰部"]}
TEAM_PROPOSED = ["天气", "行程事件", "音乐播放"]

# cross-check the drop list against the workbook so it cannot silently drift
struck_act = {r["l1"] for r in struck_rows if r["kind"] == "act"}
assert set(DROP_ACTIONS) <= struck_act, set(DROP_ACTIONS) - struck_act
struck_modes = {r["l3"] for r in struck_rows if r["kind"] == "act" and r["l2"] == "模式调节"}
assert struck_modes == {"波浪", "猫步", "蛇形", "肩部", "腰部"}, struck_modes

# --- 3. vocab
vocab = json.loads((EVAL / "vocab.json").read_text(encoding="utf-8"))
removed = {"actions": [], "action_values": {}}
for name in DROP_ACTIONS:
    if name in vocab["actions"]:
        removed["actions"].append(name); vocab["actions"].pop(name)
        vocab.get("meta", {}).get("actions", {}).pop(name, None)
for name, bad in DROP_ACT_VALUES.items():
    keep = [v for v in vocab["actions"][name] if v not in bad]
    removed["action_values"][name] = [v for v in vocab["actions"][name] if v in bad]
    vocab["actions"][name] = keep
# maturity is flattened: every surviving capability is treated the same
for kind in ("conditions", "actions"):
    for name, meta in vocab.get("meta", {}).get(kind, {}).items():
        if "maturity" in meta:
            meta["source_status"] = meta.pop("maturity")
            meta["maturity"] = "released"
vocab["_note"] = ("Round-three table. Strikethrough in 座舱原子能力-最新.xlsx removes a row outright; "
                  "everything surviving is treated equally with no maturity tier. Original workbook status kept in meta.source_status.")
(EVAL / "vocab_r3.json").write_text(json.dumps(vocab, ensure_ascii=False, indent=1), encoding="utf-8")

# --- 4. registry
reg = json.loads((EVAL / "capabilities.json").read_text(encoding="utf-8"))
dropped_caps = []
for c in reg["capabilities"]:
    if c["zh"] in DROP_ACTIONS:
        c["act_values"] = None; dropped_caps.append(c["zh"])
    if c["zh"] in DROP_ACT_VALUES and c.get("act_values"):
        c["act_values"] = [v for v in c["act_values"] if v not in DROP_ACT_VALUES[c["zh"]]]
    c["source_status"] = c.get("maturity", "released")
    c["maturity"] = "released"
    c["team_proposed"] = c["zh"] in TEAM_PROPOSED
reg["capabilities"] = [c for c in reg["capabilities"] if c.get("cond_values") or c.get("act_values")]
reg["version"] = "2026-09-08.r3"
reg["inclusion_rule"] = ("Any row with strikethrough in the source workbook is excluded. Surviving capabilities "
                         "are all equal; no released/planned/sprint/proposed distinction is made or enforced. "
                         "天气 / 行程事件 / 音乐播放 are flagged team_proposed because they are not in the workbook.")
(EVAL / "capabilities_r3.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")

prov = {"source_workbook": str(XLSX.relative_to(ROOT)),
        "workbook_sha256": hashlib.sha256(XLSX.read_bytes()).hexdigest(),
        "struck_rows": len(struck_rows), "live_rows": len(live_rows),
        "rule": "literal strikethrough exclusion, chosen by the user on 2026-09-08",
        "removed_action_capabilities": removed["actions"],
        "removed_action_values": removed["action_values"],
        "maturity": "flattened; original workbook status preserved as source_status",
        "team_proposed_kept": TEAM_PROPOSED,
        "counts": {"capabilities": len(reg["capabilities"]),
                   "with_cond_values": sum(1 for c in reg["capabilities"] if c.get("cond_values")),
                   "with_act_values": sum(1 for c in reg["capabilities"] if c.get("act_values")),
                   "vocab_conditions": len(vocab["conditions"]), "vocab_actions": len(vocab["actions"])},
        "vocab_r3_sha256": hashlib.sha256((EVAL / "vocab_r3.json").read_bytes()).hexdigest(),
        "capabilities_r3_sha256": hashlib.sha256((EVAL / "capabilities_r3.json").read_bytes()).hexdigest()}
Path(__file__).with_name("capability-provenance-r3.json").write_text(json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(prov, ensure_ascii=False, indent=2))
