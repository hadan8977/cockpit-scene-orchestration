"""v3_inline: put the contract limits inside v3's own field spec instead of an appended block. AMENDMENT-13."""
import hashlib, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent

EDITS = [
    ('"understanding": "永远是第一个字段。一句话说这个人此刻需要什么，必须引用用户原话里的词；intent 为 none 时可为空",',
     '"understanding": "永远是第一个字段，最多 80 个字符（中英文都按字符数算，超出整张被拒收）。一句话说这个人此刻需要什么，必须引用用户原话里的词；intent 为 none 时可为空",'),
    ('"name": "不超过 10 个字的场景名",',
     '"name": "不超过 10 个字符的场景名，中英文都按字符数算，英文要选短词（Anniversary 是 11 字符，不合法）",'),
    ('"say": "不超过 15 字，可以为空",',
     '"say": "不超过 15 个字符（含英文空格），可以为空",'),
    ('两类都可以用，但同一场景里这类动作不超过一个，并把它写进 warnings。',
     '两类都可以用，但同一场景里这类动作不超过一个，并把它写进 warnings；warnings 每一条必须包含完整能力名，例如 "音乐播放：尚未上线，仅供提议" 或 "进入情景模式：规划中"，只写一句解释不算。'),
]
OLD_EXAMPLE = '“dead tired” after a long day, twenty minutes left, needs the cabin to ask nothing of him'
NEW_EXAMPLE = '“dead tired” after a long day, twenty minutes left, cabin asks nothing'


def sha(d): return hashlib.sha256(d).hexdigest()


text = (HERE / "prompts/v3_latest_compatible.md").read_text(encoding="utf-8")
new = text
for old, repl in EDITS:
    assert old in new, old[:40]
    new = new.replace(old, repl, 1)
assert OLD_EXAMPLE in new
new = new.replace(OLD_EXAMPLE, NEW_EXAMPLE, 1)
over = [m.group(1) for m in re.finditer(r'\{"understanding":\s*"(.*?)",\s*"relevance"', new) if len(m.group(1)) > 80]
(HERE / "prompts/v3_inline.md").write_text(new, encoding="utf-8")
rec = {"arm": "v3_inline", "source": "prompts/v3_latest_compatible.md", "registered_in": "AMENDMENT-13.md",
       "changes": ["contract limits written into v3's own field spec lines for understanding/name/say",
                   "warnings rule states the full capability name requirement",
                   "one over-length few-shot understanding shortened 89 to 70 characters"],
       "task_logic_touched": False, "examples_added_or_removed": 0, "remaining_over_80_examples": len(over),
       "source_sha256": sha(text.encode()), "arm_sha256": sha(new.encode()), "frozen_before_first_call": True}
(HERE / "prompts/v3_inline_manifest.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(rec, ensure_ascii=False, indent=2))
