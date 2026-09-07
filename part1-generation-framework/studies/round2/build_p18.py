"""A/B hypothesis: resolve ambiguity without sacrificing useful composition."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_candidates import HERE,write

PATCH="""[completion_gate]
最后用以下规则消除歧义，优先级高于前面的泛化描述，但不减少明确的合法需求：
1. 自动化的目标设备本身不支持（例如车窗锁），不能输出一张有触发条件却没有实现目标的卡片。intent=clarify，conditions/actions=[]，unsupported准确说缺什么，问一个下一步；不要把锁窗替换成关窗。只有明确的提醒任务可保留条件、say和送达限制。
2. ‘有人时加热/heat when someone is present’缺触发席位与加热对象，必须先问哪个座位。这里不能套用立即车控默认主驾，也不能用任意座椅触发主驾加热。
3. 日期型自动化未给出年份/起止日期且上下文未知，必须追问；冬季不等于上午或温度低，不能用气温替代月份，也不能把冬季放进时段枚举。当前明确冷暖目标仍可直接给舒适提案。
4. 观察候选先数未落地能力：音乐播放、座椅按摩模式、进入情景模式等按星号计数，达到两个则clarify且conditions/actions=[]，请用户选择保留哪项。不能因为候选提供了动作就照单输出。一个*可保留并具名告知。
5. 温度越界时，只能提议边界值并warnings说明，或clarify且actions=[]；不要用action加空动作假装完成。精确阈值不满足步长必须追问，不擅自取整。
6. 英文name若超过10字符，换成短而贴切的词；周年可用Together，照明可用Glow。英文say若需要，选≤15字符的自然短句，逐字符核对；例如Take your phone太长，可用Take phone。understanding充分表达语境，不能靠空泛标题替代。
7. 明确庆生并且停车时，用一个生日相关能力（如彩蛋=生日动效，按词典成熟度告知）或适度庆祝组合，避免任何节庆都只开灯。若明确只想安静，尊重该约束。具体偏好优先于泛化氛围；丰富必须贴合，不添加无关功能。
输出前再次核对：条件忠实、所有设备覆盖、语言正确、name≤10、say≤15、最多一个*。只输出完整JSON。
"""


def main():
    base=(HERE/"prompts/p17_zh.md").read_text(encoding="utf-8")
    write("prompts/p18_zh.md",base+PATCH)
    selection=json.loads((HERE/"development-selection.json").read_text(encoding="utf-8"))
    write("plans/03_completion.json",{"run_id":"03_completion","repeat":1,"seed":71431,"ids":selection["ids"],"variants":{"p17":"prompts/p17_zh.md","p18":"prompts/p18_zh.md"}})
    write("AMENDMENT-02.md","""# 第三轮开发 A/B：完整性门

前置证据：02 中 p17 可用率 93.75%、0 次已定义安全违规；p16 为 91.41%。p17 更快，但仍存在把不支持的锁窗自动化留成空动作卡、未指明席位的自动化默认主驾、冬季日期被替换为气温/上午、观察候选照抄两个未落地动作，以及英文名称超长。

第三轮保持 p17 正文与示例、同一能力表、同一题组/参数不变，只追加 completion_gate。这测试的是一组明确的完整性规则，不冒称每条规则都已被单变量证明。H03 的原 gold 与最多一项未落地约束冲突仍保留原分母。生日的选择既记录旧 gold，也由独立评审判断是否贴切；不把改成指定亮度当作产品质量证明。

开发体验盲评 p17 对 v3_protocol 已冻结并开跑，不因后续 p18 结果取消。p18 若保留，必须单独经过全量、消融、语言交叉和新留出确认。不得把 p17 盲评当成 p18 的最终证据。
""")
    print("Prepared p18 single-block A/B: 256 calls")


if __name__=="__main__":main()
