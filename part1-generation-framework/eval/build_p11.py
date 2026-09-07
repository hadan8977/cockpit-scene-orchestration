"""Contract errata after p10 static audit; matched bilingual instructions."""
import json
from pathlib import Path
import build_p10 as P10
HERE=Path(__file__).resolve().parent

def blocks(lang):
    b=P10.blocks(lang)
    b["examples"]=b["examples"].replace("早晨", "清晨")
    if lang=="zh":
        b["safety"] += " 低速行人警报音在本能力表允许开启/微风/梦幻/无尽；正常切换这三个音色是action，不是关闭或攻击。仍绝对禁止关闭。"
        b["values"] += " 关闭规划中能力也需要带全名的warnings。声场没有后排模式，不得发明；后排哄睡可用全车模式和低音量，或不设声场。来自观察、记忆、示例的动作同样必须检查值域。"
        b["conditions"] += " 若用户要求的精确阈值不符合步长，不得照抄非法阈值，也不得擅自近似；clarify询问可支持的阈值，conditions/actions均空。"
        b["intent"] += " 上述观察路由只适用于合法候选：若忠实保留候选会违反能力值域、最多一个未发布动作等全局约束，优先clarify而不是observation，conditions/actions均空，unsupported说明冲突，请用户选择。不要悄悄删改已观察动作。"
        b["brevity"] += " name也必须跟随locale：zh用中文名，en用英文短标签。"
    else:
        b["safety"] += " This registry permits pedestrian-warning values 开启/微风/梦幻/无尽. A normal request to switch among these three sound styles is action, not disabling or an attack. 关闭 remains absolutely forbidden."
        b["values"] += " Turning OFF a planned capability still requires a warning with its full name. There is NO 后排模式 sound-stage value: never invent it. Rear-passenger lullaby may use 全车模式 with low volume, or omit sound stage. Validate values copied from observations, memories and examples too."
        b["conditions"] += " If a requested exact threshold violates the declared step, never copy the illegal threshold or silently approximate it. Clarify a supported threshold, with conditions/actions empty."
        b["intent"] += " Observation routing above applies ONLY to valid candidates. If faithfully preserving a candidate would violate global constraints such as allowed values or at most one unreleased action, clarify takes priority over observation: empty conditions/actions, explain the conflict in unsupported and ask the user to choose. Never silently alter observed actions."
        b["brevity"] += " name must follow locale too: a Chinese name for zh, a short English label for en."
    return b

def build(lang, remove=()):
    text=P10.build(lang)
    for k,old in P10.blocks(lang).items():
        new=blocks(lang)[k]
        if k in remove: text=text.replace('['+k+']\n'+old,'',1)
        elif new!=old: text=text.replace('['+k+']\n'+old,'['+k+']\n'+new,1)
    return text

if __name__=="__main__":
    for lang in ("zh", "en"):
        (HERE/"prompts"/("p11_%s.md"%lang)).write_text(build(lang),encoding="utf-8")
        (HERE/"prompts"/("p11_%s_blocks.json"%lang)).write_text(json.dumps(blocks(lang),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
