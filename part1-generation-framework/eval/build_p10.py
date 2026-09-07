"""Final-candidate revision: short-name vocabulary and explicit observation routing."""
import json
from pathlib import Path
import build_p7 as P7
import build_p9 as P9
HERE=Path(__file__).resolve().parent
NAMES="Heat/Cool/Air/Seats/Quiet/Calm/Focus/Mood/Fresh/Music/Lights/Home/Night/Winter/Rain/Travel/Camp/Rest/Scene/Rule/Alert/Custom"

def blocks(lang):
    b=P9.blocks(lang)
    if lang=="zh":
        b["brevity"]="understanding首先输出：中文6—12字，英文3—5词，最多80字符。英文name从这些短标签选择一个："+NAMES+"；中文name用2—4字。只有none/clarify的name可空。不要用Ventilation、Fragrance等超长英语单词或短语。say默认空，有用才说且任意语言≤15字符。完整紧凑JSON，不解释生成过程。"
        b["intent"] += " 安全检查后，context含【观察候选】或[Observation candidate]时必须优先observation，即使utterance写‘无’或‘none, from observation entry’。understanding不能空，要用locale语言概括条件与习惯；不是复述‘无’。观察候选relevance=0.9，不新增条件和动作。"
        b["conditions"] += " 没有当前年份/明确起止日期时，不输出季节日期区间，不写1201-0228等缺年份数据，clarify询问范围。"
        b["selection"] += " 提神需要至少一个温和的实际清醒效果：座椅通风1挡或前排风量3挡等；仅放专注音乐还不够。记忆或状态不允许时减少操作。"
    else:
        b["brevity"]="Emit understanding first: 6..12 Chinese characters or 3..5 English words, <=80 characters. Choose English name from these short labels: "+NAMES+". Chinese name uses 2..4 characters. Only none/clarify may have empty name. Never use long words such as Ventilation/Fragrance or a phrase. say defaults to empty; if useful, <=15 characters in any language. Complete compact JSON; no generation commentary."
        b["intent"] += " After safety checks, context containing 【观察候选】 or [Observation candidate] takes observation priority, even if utterance says none/from observation entry. understanding MUST summarize the conditions/habit in locale language, never empty or a repetition of 'none'. Observation relevance=0.9; add no conditions/actions."
        b["conditions"] += " Without a current year or explicit start/end dates, do not emit a seasonal date range or yearless 1201-0228. Clarify the date range."
        b["selection"] += " Energizing needs at least one gentle physical effect such as seat ventilation 1挡 or front fan 3挡; focused music alone is insufficient. Reduce intervention when preferences/state disallow it."
    samples=[
      ({"locale":"en","context":"[Observation candidate] conditions: time of day=早晨. actions: 主驾座椅加热=1挡. Seen 4 of the last 6 days.","utterance":"(none, from observation entry)"},P7.obj(understanding="Morning gentle seat heating",relevance=.9,intent="observation",name="Heat",conditions=[{"primary":"时段","op":"==","secondary":"早晨"}],actions=[{"primary":"主驾座椅加热","secondary":"1挡"}])),
      ({"locale":"zh","context":"","utterance":"冬季期间自动打开座椅加热"},P7.obj(understanding="冬季日期范围待明确",relevance=.8,intent="clarify",clarify="从哪天到哪天？"))]
    b["examples"]+='\n'+'\n'.join('INPUT: '+json.dumps(i,ensure_ascii=False,separators=(",",":"))+'\nOUTPUT: '+json.dumps(o,ensure_ascii=False,separators=(",",":")) for i,o in samples)
    return b

def build(lang,remove=()):
    text=P9.build(lang)
    for k,old in P9.blocks(lang).items():
        new=blocks(lang)[k]
        if k in remove: text=text.replace('['+k+']\n'+old,'',1)
        elif new!=old: text=text.replace('['+k+']\n'+old,'['+k+']\n'+new,1)
    return text

if __name__=="__main__":
    for lang in ("zh","en"):
        (HERE/"prompts"/("p10_%s.md"%lang)).write_text(build(lang),encoding="utf-8")
        (HERE/"prompts"/("p10_%s_blocks.json"%lang)).write_text(json.dumps(blocks(lang),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
