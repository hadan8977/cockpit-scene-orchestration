"""Test concrete boundary examples and remove redundant examples separately."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_candidates import HERE,write


def output(**change):
    obj={"understanding":"","relevance":0,"intent":"none","name":"","logic":"AND","conditions":[],"actions":[],"say":"","offer":{"type":"none","target":""},"memory":[],"unsupported":[],"warnings":[],"clarify":None}
    obj.update(change);return obj
def a(p,v):return {"primary":p,"secondary":v}
def c(p,v):return {"primary":p,"op":"==","secondary":v}


def main():
    base=(HERE/"prompts/p18_zh.md").read_text(encoding="utf-8")
    # Erratum: 'Take your phone' has exactly 15 characters, not more than 15.
    base=base.replace("例如Take your phone太长，可用Take phone。","例如Take your phone恰好15字符，也可用Take phone。")
    pairs=[
        ({"locale":"en","context":"Parked, no music preference.","utterance":"Make the cabin relaxing for a short break."},output(understanding="A calm cabin for your break",relevance=.8,intent="vague",name="Ease",actions=[a("氛围灯亮度","20%"),a("前排风量调节","1挡")],say="Take a breath")),
        ({"locale":"zh","context":"停车中，用户不喜欢香氛，喜欢灯光30%。","utterance":"想歇一会儿，按我的习惯就好。"},output(understanding="按你的习惯调柔灯光和风量",relevance=.8,intent="vague",name="小憩",actions=[a("氛围灯亮度","30%"),a("前排风量调节","1挡")],say="歇一会儿吧")),
        ({"locale":"en","context":"","utterance":"Set front seat heating to level one and rear seat ventilation to level two."},output(understanding="Warm both front seats, ventilate both rear seats",relevance=.1,intent="action",name="Seats",actions=[a("主驾座椅加热","1挡"),a("副驾座椅加热","1挡"),a("左后排座椅通风","2挡"),a("右后排座椅通风","2挡")])),
        ({"locale":"zh","context":"","utterance":"冬季一上车就自动打开暖风。"},output(understanding="需要冬季的具体日期范围",relevance=.8,intent="clarify",unsupported=["冬季日期尚未给定"],clarify="从哪天到哪天启用？")),
        ({"locale":"en","context":"","utterance":"Create a snowy evening arrival scene."},output(understanding="A gentle welcome on snowy evenings",relevance=.9,intent="precise",name="Welcome",conditions=[c("天气","雪"),c("时段","傍晚"),c("行程事件","到达")],actions=[a("主驾温度控制","25℃"),a("氛围灯亮度","30%")],say="Welcome back")),
        ({"locale":"zh","context":"【观察候选】条件：位置=公司。动作：音乐播放=专注；主驾座椅按摩模式=腰部。","utterance":""},output(understanding="候选有两项尚未落地的能力",relevance=.8,intent="clarify",unsupported=["音乐播放、主驾座椅按摩模式不能同选"],clarify="保留音乐还是按摩？")),
        ({"locale":"en","context":"","utterance":"Activate heating if somebody sits down."},output(understanding="Need the seat and heating target",relevance=.8,intent="clarify",clarify="Which seat should trigger which heater?")),
        ({"locale":"en","context":"Parked. The user wants quiet and dislikes fragrance.","utterance":"I miss somebody, and would like a little company."},output(understanding="A quiet moment with a little company",relevance=.6,intent="affect",name="Near",actions=[a("氛围灯亮度","20%"),a("音量","20%")],say="I'm here")),
    ]
    examples="\n".join("INPUT: "+json.dumps(i,ensure_ascii=False,separators=(",",":"))+"\nOUTPUT: "+json.dumps(o,ensure_ascii=False,separators=(",",":")) for i,o in pairs)
    first,rest=base.split("[examples]\n",1);old,tail=rest.split("[final_check]",1)
    # Examples reinforce useful composition instead of a universal single-light solution.
    rule="\n[composition_gate]\n舒适目标至少覆盖一个物理效果，不能仅选择未落地音乐。从目标和已知偏好选互补的光、风、温、声；通常2项，明确复杂目标可到4项；明确单控仍仅该项。任何含‘前排/front seats’的席位操作展开主驾与副驾，后排展开左后与右后，先算覆盖席位再输出。不能靠少做满足动作数量。\n"
    write("prompts/p19_zh.md",first+"[examples]\n"+old+examples+"\n[final_check]"+tail+rule)
    write("prompts/p20_zh.md",first+"[examples]\n"+examples+"\n[final_check]"+tail+rule)
    selection=json.loads((HERE/"development-selection.json").read_text(encoding="utf-8"))
    write("plans/04_examples.json",{"run_id":"04_examples","repeat":1,"seed":71432,"ids":selection["ids"],"variants":{"p18":"prompts/p18_zh.md","p19":"prompts/p19_zh.md","p20":"prompts/p20_zh.md"}})
    write("AMENDMENT-03.md","""# 第四轮开发：示例覆盖与压缩

03 中 p18 的格式/意图/名称/语言均为 100%，安全违规为 0，但相较同轮 p17，vague 类从 100% 降到 80%，仍有多座位漏项、雨夜场景丢条件。完整性文字规则未稳定转化为正确输出。

p19 增加八组具体示例及组合覆盖规则，保留已有示例；p20 只保留新增八例。p19 对 p20 只差历史示例，用于测其增量，不能以 p18→p19 当作纯单变量消融。两者对照 p18 同配置、同题组、随机交错。

顺便更正 p18 一个字符计数示例：Take your phone 恰好 15 字符。p18 原件和结果保持不动。新例不用留出题原句。新 80 题已生成并冻结，尚未调用，后续开发不以其结果改 Prompt。
""")
    print("Prepared p18/p19/p20 example A/B: 384 calls")


if __name__=="__main__":main()
