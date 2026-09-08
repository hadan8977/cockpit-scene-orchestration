"""v0_c5 / v3_c5: same prompts as _c4, plus the maturity disclosure the candidate already gets.

Fairness correction. The candidate prompt marks 23 unreleased action capabilities with `*` and the
validator charges an arm for using one without a named warning. The two baselines were never told
which capabilities are unreleased, so that charge was unearnable for them.
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
import registry

reg = registry.load()
IMM = [c["zh"] for c in reg["capabilities"]
       if c.get("status") == "enabled" and c.get("act_values") and c.get("maturity") in ("planned", "sprint", "proposed")]

ANCHOR = "规划中或提议动作写进warnings时必须包含完整能力名，例如[\"音乐播放：尚未上线，仅供提议\"]。"
DISCLOSURE = ("规划中或提议动作写进warnings时必须包含完整能力名，例如[\"音乐播放：尚未上线，仅供提议\"]。"
              "以下 %d 个动作能力尚未上线，用到其中任何一个都必须在warnings里写出它的完整能力名，"
              "且同一个场景最多只能用一个：%s。" % (len(IMM), "、".join(IMM)))

out = {}
for src, dst in [("prompts/v0_c4.md", "prompts/v0_c5.md"), ("prompts/v3_c4.md", "prompts/v3_c5.md")]:
    s = Path(src).read_text(encoding="utf-8")
    assert s.count(ANCHOR) == 1, (src, s.count(ANCHOR))
    t = s.replace(ANCHOR, DISCLOSURE)
    assert len(s.splitlines()) == len(t.splitlines())
    Path(dst).write_text(t, encoding="utf-8")
    out[dst] = {"source": src, "source_sha256": hashlib.sha256(s.encode()).hexdigest(),
                "target_sha256": hashlib.sha256(t.encode()).hexdigest(),
                "change": "the maturity disclosure is appended to the existing warnings sentence, in place; nothing else touched",
                "immature_disclosed": len(IMM), "line_count_unchanged": True}
    print(dst, "ok, sha", out[dst]["target_sha256"][:16])

man = json.loads(Path("prompts/round3_manifest.json").read_text())
man["fairness_correction"] = {
    "issue": "v0_c4 and v3_c4 were charged '规划中或提议动作缺少能力名警告' and '规划中或提议动作超过一个' although their prompts never listed which capabilities are unreleased; the candidate prompt marks all 23 with '*'. 36% of v3_c4 failures and 12% of v0_c4 failures were solely that charge.",
    "audit": "Capability membership and value ranges were checked first: v0's own embedded lists are 64 conditions and 76 actions, identical in name and in value range to the enabled registry, so no vocabulary mismatch existed. v0 also keeps conditions and actions as two separate lists, so cases like 媒体音量 used as an action violate v0's own prompt, not only the registry.",
    "fix": "v0_c5 / v3_c5 disclose the same 23 unreleased action capabilities and the same one-per-scene rule, in place on the sentence that already discussed warnings.",
    "arms": out}
Path("prompts/round3_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("manifest updated")
