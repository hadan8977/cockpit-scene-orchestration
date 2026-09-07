"""Fair baselines: state the enforced output contract to v3 and v0 without touching their task logic. AMENDMENT-11."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

CONTRACT = """
[输出契约的硬性长度与警告要求]
understanding 最多 80 个字符，中英文都按字符计，超出会被拒收。
name 最多 10 个字符，中英文都按字符计；英文场景名要选短词。
say 最多 15 个字符（含英文空格），可以为空。
规划中、提议或尚未上线的动作写进 warnings 时必须包含完整能力名，例如 ["音乐播放：尚未上线，仅供提议"] 或 ["进入情景模式：规划中"]。
"""

OLD_EXAMPLE = '“dead tired” after a long day, twenty minutes left, needs the cabin to ask nothing of him'
NEW_EXAMPLE = '“dead tired” after a long day, twenty minutes left, cabin asks nothing'


def sha(data): return hashlib.sha256(data).hexdigest()


def build(source, target, fix_example):
    text = (HERE / source).read_text(encoding="utf-8")
    changes = ["appended [输出契约的硬性长度与警告要求]"]
    new = text.rstrip("\n") + "\n" + CONTRACT
    if fix_example:
        assert OLD_EXAMPLE in new, "v3 over-length example not found"
        assert len(NEW_EXAMPLE) <= 80, len(NEW_EXAMPLE)
        new = new.replace(OLD_EXAMPLE, NEW_EXAMPLE)
        changes.append(f"shortened one few-shot understanding from {len(OLD_EXAMPLE)} to {len(NEW_EXAMPLE)} characters")
    (HERE / target).write_text(new, encoding="utf-8")
    over = [m.group(1) for m in re.finditer(r'\{"understanding":\s*"(.*?)",\s*"relevance"', new) if len(m.group(1)) > 80]
    return {"source": source, "target": target, "source_sha256": sha(text.encode()), "target_sha256": sha(new.encode()),
            "changes": changes, "remaining_over_80_examples": len(over),
            "task_logic_touched": False, "capabilities_touched": False, "examples_added_or_removed": 0}


record = {"registered_in": "AMENDMENT-11.md", "frozen_before_first_call": True, "arms": [
    build("prompts/v3_latest_compatible.md", "prompts/v3_contract.md", True),
    build("prompts/v0_latest_protocol_compatible.md", "prompts/v0_contract.md", False)]}
(HERE / "prompts/fair_baselines_manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, ensure_ascii=False, indent=2))
