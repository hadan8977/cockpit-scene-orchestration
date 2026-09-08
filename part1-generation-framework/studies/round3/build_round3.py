"""Round three arms under the v4 contract. Registered in PREREGISTRATION-round3.md before any call."""
import hashlib, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent

# The v4 contract facts, stated identically to every arm.
CONTRACT_V4 = """
[输出契约的硬性长度与警告要求]
understanding 最多 120 个字符，中英文都按字符计，超出整张被拒收。
name 最多 14 个字符，中英文都按字符计。
say 最多 30 个字符（含英文空格），可以为空。
规划中、提议或尚未上线的动作写进 warnings 时必须包含完整能力名，例如 ["音乐播放：尚未上线，仅供提议"] 或 ["进入情景模式：规划中"]。
"""

# Candidate: rewrite the three field rules for the new limits and target the judges' grounding
# definition, which penalises bare restatement and generic scenes when specific context exists.
BREVITY_V4 = """[brevity]
understanding是第一个字段，也是产品理解力的展示。它要同时做到三件事，缺一件就算没理解到位：
一，用用户自己的词说出他要的那个具体东西，不要换成泛化说法。他说“空调不凉”就写“空调不凉”，不写“车内环境需要改善”。
二，只要context里给了可用的具体事实，必须用上其中最相关的一条：人名、歌名、剩余分钟数、谁坐在哪个座位、已知的偏好数值、当前温度。有具体事实却不用，等于没理解这个人。
三，说清这组设置要达到的结果，让用户看一眼就知道为什么是这几个动作。
中文约30–45字，英文约15–22词，上限120字符。不能做的请求也先承接原话，再说清具体哪一项不能动。不要用系统规则或限制开头，不要写“用户需要…”这类机械报告，不要只把原话重复一遍就结束。未知事实不编，context里没有的人名、歌名、数值一律不写。
name中文2–5字；英文一个易懂词，最多14字符，例如Calm/Welcome/Anniversary。name对应此刻的处境，不是目的地或功能名。让不同处境有不同名字。
say只在四种情况留空：用户明确要安静、睡眠或哄睡、后排有人已睡着、只做纯数值微调。其余情况说一句自然的整话，点名这次真正写进actions的一个动作或取值，让用户不看卡片也知道车做了什么；≤30字符（含英文空格），如‘座椅热到2挡了’、‘灯调到20%，音乐也开了’、‘Seat warm at 2, light down’。不要用‘试试看’、‘好的’、‘Try this’这类没有指代的短句充数。不要说教、称呼亲爱的、臆测关系、复述整串动作或承诺接管，也不说已经执行。
未落地能力的成熟度只在warnings里写一次，understanding和say里不重复‘尚未上线/仅供提议’，也不因此改用犹豫措辞；提议本身允许，正常说清要做什么。"""

EXPERIENCE_V4 = "understanding自然说人话，直接对用户：先接住他要的东西并保留他的原词，再说具体处境、context里最相关的那条已知事实，最后说这组设置的帮助。不要‘需要改善…/需要编排…’等泛化报告，也不用规则或限制开头。只用给定的事实，不把普通累解读成驾驶失能。120字符足够写具体，例如“忙了一天还有二十分钟到家，把灯调柔、座椅按上，最后这段路轻松些”或“Twenty minutes left after a long day; soft light and a gentle massage to ease the way home”。say按上面的留空规则；开口时点名一个已写入的动作或取值，温暖且有用，不声称接管/已经执行，不说教‘深呼吸’，不用‘亲爱的’；不用空话装关怀。咨询怎么设置时说‘可以这样搭配…’而非机械重复需求。"

CHECK_OLD = "输出前再次核对：条件忠实、所有设备覆盖、语言正确、name≤10、say≤15、最多一个*。只输出完整JSON。"
CHECK_NEW = "输出前再次核对：条件忠实、所有设备覆盖、语言正确、understanding≤120、name≤14、say≤30、最多一个*，understanding里用上了context里最相关的一条具体事实。只输出完整JSON。"
RULE6_OLD = "6. 英文name若超过10字符，换成短而贴切的词；周年可用Together，照明可用Glow。英文say若需要，选≤15字符的自然短句，逐字符核对；例如Take your phone恰好15字符，也可用Take phone。understanding充分表达语境，不能靠空泛标题替代。"
RULE6_NEW = "6. 英文name最多14字符，Anniversary合法；照明可用Glow。英文say若需要，选≤30字符的自然短句，逐字符核对。understanding必须充分表达语境并用上context里最相关的一条具体事实，不能靠空泛标题替代。"


def sha(d): return hashlib.sha256(d).hexdigest()


def baseline(src, dst, fix_example=False):
    t = (HERE / src).read_text(encoding="utf-8")
    new = t.rstrip("\n") + "\n" + CONTRACT_V4
    changes = ["appended the v4 contract facts"]
    if fix_example:
        old = '“dead tired” after a long day, twenty minutes left, needs the cabin to ask nothing of him'
        if old in new:
            changes.append("example already within 120 characters, left unchanged")
    (HERE / dst).write_text(new, encoding="utf-8")
    return {"source": src, "target": dst, "changes": changes, "task_logic_touched": False,
            "source_sha256": sha(t.encode()), "target_sha256": sha(new.encode())}


def candidate():
    t = (HERE / "prompts/p26_zh.md").read_text(encoding="utf-8")
    new, n = re.subn(r"\[brevity\]\n.*?(?=\n\[)", BREVITY_V4, t, count=1, flags=re.S)
    assert n == 1
    old_par = [l for l in t.splitlines() if l.startswith("understanding自然说人话")]
    assert len(old_par) == 1
    new = new.replace(old_par[0], EXPERIENCE_V4, 1)
    assert CHECK_OLD in new and RULE6_OLD in new
    new = new.replace(CHECK_OLD, CHECK_NEW, 1).replace(RULE6_OLD, RULE6_NEW, 1)
    (HERE / "prompts/p28_zh.md").write_text(new, encoding="utf-8")
    return {"candidate": "p28", "parent": "p26",
            "changes": ["brevity block rewritten for the v4 limits and the judges' grounding definition",
                        "complete_experience wording paragraph rewritten",
                        "completion_gate rule 6 and the final checklist updated to the v4 limits"],
            "parent_sha256": sha(t.encode()), "candidate_sha256": sha(new.encode()),
            "parent_chars": len(t), "candidate_chars": len(new)}


rec = {"contract": "v4", "registered_in": "PREREGISTRATION-round3.md", "frozen_before_first_call": True,
       "limits": {"understanding": 120, "name": 14, "say": 30},
       "arms": [baseline("prompts/v0_latest_protocol_compatible.md", "prompts/v0_c4.md"),
                baseline("prompts/v3_latest_compatible.md", "prompts/v3_c4.md", True),
                candidate()]}
(HERE / "prompts/round3_manifest.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(rec, ensure_ascii=False, indent=2))
