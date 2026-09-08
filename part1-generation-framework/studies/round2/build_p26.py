"""p26: rewrite the wording block and add task-completion rules on top of p24. Registered in AMENDMENT-10."""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BREVITY = """[brevity]
understanding是第一个字段，也是产品理解力的展示：先用用户自己的话承接他要什么，再说这组设置帮他达到什么；不能做的请求也先承接，再说清具体哪一项不能动。不要用系统规则或限制开头。中文约16–30字，英文约8–12词，最终≤80字符；简单控制可短，但不使用‘用户需要…’的机械报告。未知事实不编。
name中文2–4字；英文一个易懂词，最多10字符，例如Calm/Welcome/Together，不用11字符Anniversary。name对应此刻的处境，不是目的地或功能名。让不同处境有不同名字。
say只在四种情况留空：用户明确要安静、睡眠或哄睡、后排有人已睡着、只做纯数值微调。其余情况给一句具体的话，点名这次真正写进actions的一个动作或取值，让用户不看卡片也知道车做了什么；≤15字符（包括英文空格），逐字符核对，如‘座椅热2挡了’、‘灯调到20%’、‘Seat warm, L2’、‘Soft light on’。不要用‘试试看’、‘好的’、‘Try this’这类没有指代的短句充数。不要说教、称呼亲爱的、臆测关系、复述整串动作或承诺接管，也不说已经执行。
未落地能力的成熟度只在warnings里写一次，understanding和say里不重复‘尚未上线/仅供提议’，也不因此改用犹豫措辞；提议本身允许，正常说清要做什么。
understanding/name/say/clarify及解释性warnings/unsupported随locale；能力名和值保持词典中文。
"""

EXPERIENCE = "understanding自然说人话，直接对用户：先接住他要的东西，再说具体处境、重要已知数字/对象和这组设置的帮助。不要‘需要改善…/需要编排…’等泛化报告，也不用规则或限制开头。只用给定的事实，不把普通累解读成驾驶失能。英文≤80字符仍可具体，如“Twenty minutes home; soft light and gentle massage can ease the last stretch”。say按上面的留空规则；开口时点名一个已写入的动作或取值，温暖且有用，不声称接管/已经执行，不说教‘深呼吸’，不用‘亲爱的’；不用空话装关怀。咨询怎么设置时说‘可以这样搭配…’而非机械重复需求。"

TASK_RULES = """8. 明确的提醒/通知任务用小塔播报的自定义内容承接，actions不能为空。‘到公司停好车提醒我带电脑’要给出条件加小塔播报=自定义内容，不要只写unsupported。送达方式受限时在warnings说明，仍保留这条动作。
9. 同一语义有released条件时，不用成熟度更低的条件。‘停好车/到站停车’用挡位==挡位P，不用行程事件==到达；‘出发/离车’没有released替代才用行程事件。
10. 哄睡与安静场景在夜间同时把灯光降下来，不只做声场和音量；已知当前是夜间或车内灯已亮时尤其如此。
11. 提神、清醒、透气类目标的风量不超过2挡，优先通风与换气；不要用3挡风量制造存在感。
"""


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    src = HERE / "prompts/p24_zh.md"
    text = src.read_text(encoding="utf-8")
    before = sha(text.encode())

    new, count = re.subn(r"\[brevity\]\n.*?(?=\n\[)", BREVITY.rstrip("\n"), text, count=1, flags=re.S)
    assert count == 1, "brevity block not matched"

    old_paragraph = [l for l in text.splitlines() if l.startswith("understanding自然说人话")]
    assert len(old_paragraph) == 1, old_paragraph
    new = new.replace(old_paragraph[0], EXPERIENCE, 1)

    anchor = "输出前再次核对：条件忠实、所有设备覆盖、语言正确、name≤10、say≤15、最多一个*。只输出完整JSON。"
    assert anchor in new
    new = new.replace(anchor, TASK_RULES + anchor, 1)

    out = HERE / "prompts/p26_zh.md"
    out.write_text(new, encoding="utf-8")
    record = {
        "candidate": "p26",
        "parent": "p24",
        "registered_in": "AMENDMENT-10.md",
        "changed_blocks": ["brevity", "complete_experience paragraph 2", "completion_gate rules 8-11"],
        "parent_sha256": before,
        "candidate_sha256": sha(new.encode()),
        "parent_chars": len(text),
        "candidate_chars": len(new),
        "frozen_before_first_call": True,
    }
    (HERE / "prompts/p26_manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
