"""v0_r3 / v3_r3: the baselines carrying the identical round-three capability table.

Minimal in-place edits so ordering and wording stay as the colleague wrote them: the four door
actions are dropped, the two massage-mode value lists shrink to 关闭, and the maturity sentence goes
away because there is no maturity tier any more. The result is asserted equal to the table the
candidate is given.
"""
import hashlib, json, os, re, sys
from pathlib import Path
os.environ["SCENE_CAPS"] = "r3"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
import contract_limits as CL
V = json.loads((ROOT / "eval" / CL.VOCAB_FILE).read_text(encoding="utf-8"))

MATURITY_SENTENCE = "规划中或提议动作写进warnings时必须包含完整能力名，例如[\"音乐播放：尚未上线，仅供提议\"]。"

def patch(src, dst):
    s = Path(src).read_text(encoding="utf-8")
    out = s
    for var, kind in (("allConditions", "conditions"), ("c", "actions")):
        m = re.search(r"const %s = (\[.*?\]);" % var, out, re.S)
        arr = json.loads(m.group(1))
        new = []
        for d in arr:
            name = d["primary"]
            if name not in V[kind]:
                continue                                  # dropped by the strikethrough rule
            spec = V[kind][name]
            d = dict(d, secondary=(spec if isinstance(spec, list) else {"range": spec["range"]}))
            new.append(d)
        # the baseline table must now be exactly the harness table
        assert {d["primary"] for d in new} == set(V[kind]), \
            (kind, set(V[kind]) - {d["primary"] for d in new}, {d["primary"] for d in new} - set(V[kind]))
        out = out[:m.start(1)] + json.dumps(new, ensure_ascii=False, separators=(",", ":")) + out[m.end(1):]
    assert out.count(MATURITY_SENTENCE) == 1
    out = out.replace(MATURITY_SENTENCE, "能力表里的每一条都同等可用，不分上线状态，不需要为任何一条在warnings里加成熟度说明。")
    assert len(s.splitlines()) == len(out.splitlines())
    Path(dst).write_text(out, encoding="utf-8")
    return {"source": src, "target": dst,
            "source_sha256": hashlib.sha256(s.encode()).hexdigest(),
            "target_sha256": hashlib.sha256(out.encode()).hexdigest()}

# v3 uses a rendered natural-language table and is handled by build_v3_r3.py
info = [patch(ROOT / "studies/round3/prompts/v0_c4.md", ROOT / "studies/round3/prompts/v0_r3.md")]
for i in info:
    print(Path(i["target"]).name, "->", i["target_sha256"][:16])
print("conditions %d, actions %d — identical to the table the candidate receives" % (len(V["conditions"]), len(V["actions"])))
