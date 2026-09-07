"""p27: narrow rule 9 and harden the English say character count on top of p26. Registered in AMENDMENT-12."""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent

OLD9 = "9. 同一语义有released条件时，不用成熟度更低的条件。‘停好车/到站停车’用挡位==挡位P，不用行程事件==到达；‘出发/离车’没有released替代才用行程事件。"
NEW9 = "9. 用户点名了目的地或说了‘到某地’，触发条件用行程事件==到达，这是到达语义的直接表达；只有单说‘停好车/熄火后’而没有目的地时，才用released的挡位==挡位P。两者不叠加，选一个最贴原话的。"

OLD_SAY_TAIL = "不要用‘试试看’、‘好的’、‘Try this’这类没有指代的短句充数。"
NEW_SAY_TAIL = "英文say先逐字符数一遍再输出，含空格超过15就换更短的说法：‘Seat at 3, wheel on’是19字符不合法，改成‘Seat 3, wheel on’仍超，用‘Seat 3, warm’；‘Happy anniversary’17字符改成‘Happy day’。宁可少点名一个动作，也不能超限。不要用‘试试看’、‘好的’、‘Try this’这类没有指代的短句充数。"


def sha(d): return hashlib.sha256(d).hexdigest()


text = (HERE / "prompts/p26_zh.md").read_text(encoding="utf-8")
assert OLD9 in text and OLD_SAY_TAIL in text
new = text.replace(OLD9, NEW9, 1).replace(OLD_SAY_TAIL, NEW_SAY_TAIL, 1)
(HERE / "prompts/p27_zh.md").write_text(new, encoding="utf-8")
rec = {"candidate": "p27", "parent": "p26", "registered_in": "AMENDMENT-12.md",
       "changes": ["completion_gate rule 9 narrowed to parking-without-destination",
                   "brevity say rule adds explicit English character counting with worked examples"],
       "parent_sha256": sha(text.encode()), "candidate_sha256": sha(new.encode()),
       "frozen_before_first_call": True}
(HERE / "prompts/p27_manifest.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(rec, ensure_ascii=False, indent=2))
