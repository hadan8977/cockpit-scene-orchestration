"""Second development screen: preserve p13 boundaries, vary experience/compression."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_candidates import HERE,EVAL,write


def main():
    original=(EVAL/"prompts/p13_zh.md").read_text(encoding="utf-8")
    old=json.loads((EVAL/"prompts/p13_zh_blocks.json").read_text(encoding="utf-8"))
    new=dict(old)
    new["selection"]=old["selection"]+"\n完整而克制：明确创建场景、明确舒适目标，优先选择2–4个互补动作以覆盖目标；如果一项已经足够就只做一项。只是当前情绪状态则1–2个贴切动作，不动无关设备。具体设备命令必须完整，不为凑数量补动作。不要所有场景只调暗灯：根据处境、已知偏好和物理目标变化手段。想念优先已知的歌曲与偏好灯光；短休息可暗灯与低风量，明确点名按摩则用按摩；安静睡眠选声场和音量；提神优先通风、风量与专注，闷热优先换气/降温。若知道具体偏好值，用它而不是默认值。规划中/提议动作最多一个，按摩模式与音乐二选一，绝不能组合两个未落地动作。停车生日庆祝可亮度50%或生日彩蛋；行驶必须守亮度50%与禁止律动。相同功能的开关+值可以必要配套，不用它们冒充丰富的跨功能组合。"
    new["brevity"]="understanding首字段，抓住本句的具体对象或处境和要达到的结果，用自然一句话表达；包含原话关键词，不用‘用户需要…’的机械说明，不臆测没有给出的关系。中文约10–20字、英文约5–9词且均≤80字符。name中文2–4字，英文一个≤10字母的合适词，不能用带空格长短语。say有确认或陪伴价值时可自然说一句，所有语言≤15字符；纯操作、安静、睡着、不要说话时为空，不能每次都说同一套话。所有用户可见文案按locale；能力名和值仍用词典原文。不要声称已执行、保存、代用户决定，不说教，不重复猜测情绪。输出紧凑JSON。"
    new["intent"]=old["intent"]+"\n条件识别优先于动作：明确写了when/whenever/at某时刻/到了/低于…就…，即使句末还有多个动作，也必须保留触发条件。明确创建带天气/时段/目的地修饰的场景，要保留这些合法条件，不把它当无条件舒适提案。用户自己的‘我叫…/I am…/My name is…’是第一人称事实，不因姓名或单词owner误当第三方注入；‘车主喜欢…/the owner likes…’才是第三方转述。单独切换低速行人警报音微风/梦幻/无尽是正常动作，不等于关闭安全功能。"
    text=original
    for key in ("selection","brevity","intent"):
        assert "["+key+"]\n"+old[key] in text
        text=text.replace("["+key+"]\n"+old[key],"["+key+"]\n"+new[key],1)
    write("prompts/p16_zh.md",text)
    write("prompts/p16_blocks.json",new)
    # Explicit paired-example compression. Retain routing/safety/value blocks verbatim.
    examples=old["examples"].splitlines()
    pairs=[examples[i:i+2] for i in range(0,len(examples),2)]
    indices=[0,1,2,3,4,5,6,7,8,10,12,15,16,18,20,22,24,25,26,27]
    reduced="\n".join(line for i in indices if i<len(pairs) for line in pairs[i])
    compressed=text.replace("[examples]\n"+old["examples"],"[examples]\n"+reduced,1)
    write("prompts/p17_zh.md",compressed)
    common="\n[所有本轮对照共用的输出协议约定]\n"+old["role"]+"\n"+old["contract"]+"\nintent只用action/precise/vague/affect/observation/clarify/none；旧标签conditional对应precise，fuzzy对应vague，direct对应action。understanding最多80字符，name最多10字符，say最多15字符；这些是统一协议长度，不改变前文的意图和组合策略。secondary必须是字符串，日期时间使用当前能力契约。\n"
    for name in ("v0_latest_protocol","v3_latest"):
        write("prompts/"+name+"_compatible.md",(HERE/("prompts/"+name+".md")).read_text(encoding="utf-8")+common)
    selection=json.loads((HERE/"development-selection.json").read_text(encoding="utf-8"))
    write("plans/02_refinement.json",{"run_id":"02_refinement","repeat":1,"seed":71430,"ids":selection["ids"],"variants":{"p16":"prompts/p16_zh.md","p17":"prompts/p17_zh.md","v3_protocol":"prompts/v3_latest_compatible.md","v0_protocol":"prompts/v0_latest_protocol_compatible.md"}})
    print(json.dumps({"p16_bytes":len(text.encode()),"p17_bytes":len(compressed.encode()),"calls":512,"kept_example_indices":indices}))


if __name__=="__main__":main()
