"""Export anonymous pairs for optional human review; does not invent human ratings."""
import json
from pathlib import Path
from safe_eval import read_rows
HERE=Path(__file__).resolve().parent
p=HERE/"results"/"prompt-lab-v3"/"09_blind_review"
lines=["# 匿名体验评审表（人工尚未评分）", "", "每个 A/B 是同一输入与状态下的场景提议，尚未执行。分别按 1—5 分评贴切、分寸、话术、组合；5=完全合适，4=小问题，3=可用但有明显问题，2=需要大改，1=有害或不相关。不要因字多、动作多而加分；安静或已拒绝时不动作可能是最佳答案。", "", "分寸包括是否遵守安静、偏好和之前的拒绝；话术包括语言自然、简洁、无说教、无虚假执行宣称。模型版本映射单独保存，评审前无需查看。", ""]
for s in read_rows(p/"samples.jsonl"):
    lines += ["## "+s["sample_id"]+" · "+s["locale"], "", "```json", json.dumps({"input":s["input"],"context":s["context"]},ensure_ascii=False,indent=2), "```", ""]
    for side in ("A", "B"):
        lines += ["### "+side, "", "```json", s[side], "```", ""]
    lines += ["| 候选 | 贴切 | 分寸 | 话术 | 组合 | 理由 |", "|---|---|---|---|---|---|", "| A | | | | | |", "| B | | | | | |", "", "偏好：A / B / 相当（待填）", ""]
(p/"human-review.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("Wrote anonymous human-review.md; no ratings filled")
