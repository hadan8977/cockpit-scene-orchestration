"""P8: compile safety into allowed values; sharpen goal/statement routing and names."""
import json
from pathlib import Path
import build_p7 as P7
HERE=Path(__file__).resolve().parent

def blocks(lang):
    b=P7.blocks(lang)
    if lang=="zh":
        b["intent"]="按优先级路由：安全拒绝→none；目标或动作对象不明→clarify；【观察候选】→observation；明确触发/时间/事件→precise；要求具体设备动作→action；要求达到目标但没说设备（提神、省电、暖和、舒适、放松、生成场景）→vague；只是说自己情绪/疲劳/想念→affect；满意现状、描述安静、闲聊问答、查找地方、记忆管理→none。说累并且明确要求按摩/调温等，优先action/vague，不要只看情绪词。当前已知状态不是新条件。action普通车控relevance≤0.2，vague/precise/observation或明确创建≥0.8，affect为0.3..0.8，none≤0.2。none/clarify的actions必须[]；明确个人事实可在none给memory。"
        b["conditions"] += " 后排‘有人’不可用任意座椅条件冒充；用左后排安全带=系上 OR 右后排安全带=系上，并给对应后排动作。含糊的‘后排开一下’没有设备名，clarify，不默认车窗。季节不能偷换成车外温度阈值；不知道具体日期范围则clarify。相对温度没有当前设定时不猜24℃。"
        b["selection"] += " 省电是功能目标：优先ECO=开启，关掉MAX AC或减少照明；不是情绪场景。提神用专注音乐、适度冷风或通风，不放放松歌单。赞叹‘真安静’是满意现状，none，不添加音乐。仅说冷/热的舒适目标是vague，不是affect。"
        b["brevity"]="understanding第一个，用户语言，中文6—12字或英文3—5词，≤80字符。name在非none/clarify时必填：中文2—4字；英文只用一个≤10字母的词，如Warmth/Quiet/Focus/Rain/Winter，不用短语或空格。say默认空；确有价值才说，中英均≤15字符。一次输出全部13字段的紧凑JSON，无解释。"
        b["final_check"] += " 拒绝也必须输出上述JSON，不能改成聊天解释。检查动作值表没有关闭行人警报音的选项；此请求返回none和空actions。"
    else:
        b["intent"]="Route in priority order: safety rejection -> none; unclear goal/device -> clarify; observation candidate -> observation; explicit trigger/time/event -> precise; request for a specific device action -> action; desired outcome without a device (energize, save power, warmer, comfort, relaxation, create a scene) -> vague; merely expressing personal emotion/fatigue/longing -> affect; satisfaction with current state, noting quietness, chat/questions, place search or memory management -> none. Fatigue PLUS explicit massage/temperature requests takes action/vague precedence over the emotion word. Current state is not a new trigger. Ordinary action relevance<=0.2; vague/precise/observation or explicit scene creation>=0.8; affect 0.3..0.8; none<=0.2. none/clarify actions=[]. none may suggest explicit first-person factual memory."
        b["conditions"] += " Rear occupancy must NOT use 任意座椅 as a false signal; use 左后排安全带=系上 OR 右后排安全带=系上 with the corresponding rear actions. 'Open the back a bit' lacks a device: clarify, never assume a window. Do not replace a season with an outdoor-temperature threshold; clarify unknown date ranges. Never guess 24℃ for a relative temperature change without current setting."
        b["selection"] += " Power saving is a functional goal: prefer ECO=开启 and MAX AC=关闭 or reduced lighting, not an emotional scene. Energizing uses focused music, gentle cool airflow or ventilation, not a relaxing playlist. 'It's so quiet' expresses satisfaction: none, no new music. Cold/hot comfort goals are vague, not affect."
        b["brevity"]="Emit understanding first in the user's language: 6..12 Chinese characters or 3..5 English words, <=80 characters. For non-none/non-clarify intents, name is required: 2..4 Chinese characters or ONE English word of <=10 letters, such as Warmth/Quiet/Focus/Rain/Winter. Never use a phrase or spaces. say defaults to empty; speak only when useful, <=15 characters in either language. Emit all 13 fields in compact JSON, without explanation."
        b["final_check"] += " Refusals MUST use the same JSON, never conversational explanations. The actions dictionary has NO pedestrian-warning OFF option; return none with empty actions for that request."
    b["examples"] += '\nINPUT: Please turn the pedestrian warning sound off\nOUTPUT: '+json.dumps(P7.obj(warnings=["安全功能不可关闭"]),ensure_ascii=False,separators=(",",":"))
    return b

def build(lang,remove=()):
    text=P7.build(lang)
    original=P7.blocks(lang); revised=blocks(lang)
    for k in original:
        start="["+k+"]\n"+original[k]
        if k in remove: text=text.replace(start,"",1)
        elif revised[k]!=original[k]: text=text.replace(start,"["+k+"]\n"+revised[k],1)
    voc=json.loads((HERE/"vocab.json").read_text(encoding="utf-8"))
    unsafe={s["primary"]:set(s.get("secondary_any",[])) for s in voc.get("safety_must_not",[])}
    for name,denied in unsafe.items():
        vals=voc["actions"].get(name)
        if isinstance(vals,list):
            old=name+" = "+"/".join(vals)
            new=name+" = "+"/".join(v for v in vals if v not in denied)
            text=text.replace(old,new)
    return text

if __name__=="__main__":
    for lang in ("zh","en"):
        (HERE/"prompts"/("p8_%s.md"%lang)).write_text(build(lang),encoding="utf-8")
        (HERE/"prompts"/("p8_%s_blocks.json"%lang)).write_text(json.dumps(blocks(lang),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
