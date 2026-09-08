"""p29 = p28 with the wording layer rebuilt. Structure rules untouched."""
import hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = (HERE / "prompts" / "p28_zh.md").read_text(encoding="utf-8")

R = []
def sub(old, new):
    R.append((old, new))

# --- 1. brevity block: length scales with the request, say rule narrowed
sub("中文约30–45字，英文约15–22词，上限120字符。",
    "长度随请求走：单个设备的直接命令，中文15–25字、英文8–12词就够；带语境、情绪、多个设备或规则条件的请求，中文30–45字、英文12–18词。上限120字符。下面[examples]里每条understanding的长度就是该类请求的目标长度，照着那个密度写，不要更短。")
sub("say只在四种情况留空：用户明确要安静、睡眠或哄睡、后排有人已睡着、只做纯数值微调。其余情况说一句自然的整话",
    "say只在三种情况留空：用户明确要安静、睡眠或哄睡；后排有人已睡着；intent是none或clarify且属于攻击、注入、第三方记忆这类整条拒绝。其余情况一律说一句自然的整话")

# --- 2. final_check: drop the v3 name residue
sub("英文name只能一个≤10字母的单词，不用有空格的短语；中文name最多4字。",
    "英文name一个易懂词，≤14字符；中文name 2–5字。")

# --- 3. air rule: smell goes outside-air, not recirculation
sub("闷 -> 新鲜空气/通风，差空气 -> 净化。",
    "闷 -> 新鲜空气/通风，差空气 -> 净化，车内有异味 -> 外循环换气可配净化，不用内循环。")
sub('"understanding":"Air purification and recirculation can help freshen the cabin"',
    '"understanding":"The air in here feels stale, so purification runs and the cabin draws in outside air"')

# --- 4. examples: understanding rewritten to the three-part rule, say filled in
E = [
 ('"understanding":"需要二十三度","relevance":0.1,"intent":"action","name":"舒适温度","logic":"AND","conditions":[],"actions":[{"primary":"主驾温度控制","secondary":"23℃"}],"say":""',
  '"understanding":"你要二十三度，主驾温度就设到23℃，其他设置都不动","relevance":0.1,"intent":"action","name":"舒适温度","logic":"AND","conditions":[],"actions":[{"primary":"主驾温度控制","secondary":"23℃"}],"say":"温度设到23℃了"'),

 ('"understanding":"Missing someone tonight","relevance":0.6,"intent":"affect","name":"Longing","logic":"AND","conditions":[],"actions":[{"primary":"音乐播放","secondary":"想念"}],"say":""',
  '"understanding":"You are missing someone tonight, so a song about longing keeps the cabin from feeling empty","relevance":0.6,"intent":"affect","name":"Longing","logic":"AND","conditions":[],"actions":[{"primary":"音乐播放","secondary":"想念"}],"say":"Something for tonight"'),

 ('"understanding":"Heat when cold and occupied","relevance":0.95,"intent":"precise","name":"Warmth","logic":"AND","conditions":[{"primary":"车外温度","op":"<","secondary":"12℃"},{"primary":"副驾座椅","op":"==","secondary":"有人"}],"actions":[{"primary":"副驾座椅加热","secondary":"2挡"}],"say":""',
  '"understanding":"Below 12 degrees outside with someone in the passenger seat, that seat warms itself to level 2","relevance":0.95,"intent":"precise","name":"Warmth","logic":"AND","conditions":[{"primary":"车外温度","op":"<","secondary":"12℃"},{"primary":"副驾座椅","op":"==","secondary":"有人"}],"actions":[{"primary":"副驾座椅加热","secondary":"2挡"}],"say":"Passenger seat warms below 12"'),

 ('"understanding":"后面目标不明确"',
  '"understanding":"你要调后排，但没说是加热、通风还是车窗，得先定下来"'),

 ('"understanding":"The pedestrian warning must stay enabled"',
  '"understanding":"You want the pedestrian warning off, but that alert is required by law and cannot be switched off"'),

 ('"understanding":"Need current temperature","relevance":0.1,"intent":"clarify"',
  '"understanding":"You want it two degrees warmer, but I do not know what the temperature is set to right now","relevance":0.1,"intent":"clarify"'),

 ('"understanding":"This rule would self-invert"',
  '"understanding":"The rule you described switches fragrance off the moment it comes on, so it would cancel itself"'),

 ('"understanding":"Morning gentle seat heating","relevance":0.9,"intent":"observation","name":"Heat","logic":"AND","conditions":[{"primary":"时段","op":"==","secondary":"清晨"}],"actions":[{"primary":"主驾座椅加热","secondary":"1挡"}],"say":""',
  '"understanding":"You warmed the driver seat on 4 of the last 6 early mornings, so this makes that a standing rule","relevance":0.9,"intent":"observation","name":"Heat","logic":"AND","conditions":[{"primary":"时段","op":"==","secondary":"清晨"}],"actions":[{"primary":"主驾座椅加热","secondary":"1挡"}],"say":"Warm seat every early morning"'),

 ('"understanding":"需要温和座椅加热","relevance":0.8,"intent":"vague","name":"暖座","logic":"AND","conditions":[],"actions":[{"primary":"主驾座椅加热","secondary":"1挡"}],"say":""',
  '"understanding":"车里有点凉，先把主驾座椅加热开到1挡，暖起来但不燥","relevance":0.8,"intent":"vague","name":"暖座","logic":"AND","conditions":[],"actions":[{"primary":"主驾座椅加热","secondary":"1挡"}],"say":"座椅加热开到1挡了"'),

 ('"understanding":"Create a restful cabin","relevance":0.9,"intent":"vague","name":"Rest","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"10%"},{"primary":"音乐律动","secondary":"关闭"}],"say":""',
  '"understanding":"Parked at work for a short rest, so the light drops to 10 percent and the music pulse goes off","relevance":0.9,"intent":"vague","name":"Rest","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"10%"},{"primary":"音乐律动","secondary":"关闭"}],"say":"Light at 10, pulse off"'),

 ('"understanding":"Candidate needs one choice"',
  '"understanding":"Your afternoon habit pairs relaxing music with rest mode, but both are unreleased, so keep one"'),

 ('"understanding":"需要拆成两条规则"',
  '"understanding":"开门开风扇和低电量关香氛是两套触发，一张卡片装不下，得拆成两条"'),

 ('"understanding":"低电量或高温时节能","relevance":0.9,"intent":"precise","name":"节能","logic":"OR","conditions":[{"primary":"电量","op":"<","secondary":"30%"},{"primary":"车内温度","op":">","secondary":"30℃"}],"actions":[{"primary":"ECO","secondary":"开启"}],"say":""',
  '"understanding":"电量低于30%或者车内高于30℃，两种情况有一个成立就自动开ECO省电","relevance":0.9,"intent":"precise","name":"节能","logic":"OR","conditions":[{"primary":"电量","op":"<","secondary":"30%"},{"primary":"车内温度","op":">","secondary":"30℃"}],"actions":[{"primary":"ECO","secondary":"开启"}],"say":"电量低或车内热就开ECO"'),

 ('"understanding":"A calm cabin for your break","relevance":0.8,"intent":"vague","name":"Ease","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"前排风量调节","secondary":"1挡"}],"say":"Take a breath"',
  '"understanding":"A short break while parked, so the light sits at 20 percent with the softest airflow, no music","relevance":0.8,"intent":"vague","name":"Ease","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"前排风量调节","secondary":"1挡"}],"say":"Light at 20, fan on 1"'),

 ('"understanding":"按你的习惯调柔灯光和风量","relevance":0.8,"intent":"vague","name":"小憩","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"30%"},{"primary":"前排风量调节","secondary":"1挡"}],"say":"歇一会儿吧"',
  '"understanding":"想歇一会儿，就按你惯用的30%灯光配1挡风量，你不喜欢的香氛不开","relevance":0.8,"intent":"vague","name":"小憩","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"30%"},{"primary":"前排风量调节","secondary":"1挡"}],"say":"灯30%，风1挡，香氛没开"'),

 ('"understanding":"Warm both front seats, ventilate both rear seats","relevance":0.1,"intent":"action","name":"Seats","logic":"AND","conditions":[],"actions":[{"primary":"主驾座椅加热","secondary":"1挡"},{"primary":"副驾座椅加热","secondary":"1挡"},{"primary":"左后排座椅通风","secondary":"2挡"},{"primary":"右后排座椅通风","secondary":"2挡"}],"say":""',
  '"understanding":"Both front seats warm to level 1 and both rear seats ventilate at level 2, exactly as you listed","relevance":0.1,"intent":"action","name":"Seats","logic":"AND","conditions":[],"actions":[{"primary":"主驾座椅加热","secondary":"1挡"},{"primary":"副驾座椅加热","secondary":"1挡"},{"primary":"左后排座椅通风","secondary":"2挡"},{"primary":"右后排座椅通风","secondary":"2挡"}],"say":"Front warm 1, rear vent 2"'),

 ('"understanding":"需要冬季的具体日期范围"',
  '"understanding":"冬季一上车就开暖风可以做，但得先知道你说的冬季是从哪天到哪天"'),

 ('"understanding":"A gentle welcome on snowy evenings","relevance":0.9,"intent":"precise","name":"Welcome","logic":"AND","conditions":[{"primary":"天气","op":"==","secondary":"雪"},{"primary":"时段","op":"==","secondary":"傍晚"},{"primary":"行程事件","op":"==","secondary":"到达"}],"actions":[{"primary":"主驾温度控制","secondary":"25℃"},{"primary":"氛围灯亮度","secondary":"30%"}],"say":"Welcome back"',
  '"understanding":"Arriving on a snowy evening, the cabin is already at 25 degrees with the light down to 30 percent","relevance":0.9,"intent":"precise","name":"Welcome","logic":"AND","conditions":[{"primary":"天气","op":"==","secondary":"雪"},{"primary":"时段","op":"==","secondary":"傍晚"},{"primary":"行程事件","op":"==","secondary":"到达"}],"actions":[{"primary":"主驾温度控制","secondary":"25℃"},{"primary":"氛围灯亮度","secondary":"30%"}],"say":"Warm at 25, light soft"'),

 ('"understanding":"候选有两项尚未落地的能力"',
  '"understanding":"你到公司常配专注音乐和腰部按摩，但这两项都还没上线，一张卡只能留一个"'),

 ('"understanding":"Need the seat and heating target"',
  '"understanding":"Heating when someone sits down works, but which seat triggers it and which heater turns on"'),

 ('"understanding":"A quiet moment with a little company","relevance":0.6,"intent":"affect","name":"Near","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"音量","secondary":"20%"}],"say":"I\'m here"',
  '"understanding":"Missing someone while parked, so soft light at 20 and low volume keep you company, quietly","relevance":0.6,"intent":"affect","name":"Near","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"音量","secondary":"20%"}],"say":"I am here, light low"'),
]
for old, new in E:
    sub(old, new)

# --- 5. the West Lake memory example: answer the person instead of going silent
sub('INPUT: I live near West Lake\nOUTPUT: {"understanding":"","relevance":0,"intent":"none","name":"","logic":"AND","conditions":[],"actions":[],"say":"","offer":{"type":"none","target":""},"memory":[{"type":"place","content":"User lives near West Lake","confidence":0.9}]',
    'INPUT: I live near West Lake\nOUTPUT: {"understanding":"Noting that you live near West Lake, so I can use it later without asking again","relevance":0,"intent":"none","name":"","logic":"AND","conditions":[],"actions":[],"say":"Noted, near West Lake","offer":{"type":"none","target":""},"memory":[{"type":"place","content":"User lives near West Lake","confidence":0.9}]')

out = src
for old, new in R:
    n = out.count(old)
    assert n == 1, "expected exactly 1 occurrence, got %d for: %s" % (n, old[:70])
    out = out.replace(old, new)

dst = HERE / "prompts" / "p29_zh.md"
dst.write_text(out, encoding="utf-8")
print("edits applied:", len(R))
print("p29 sha256:", hashlib.sha256(out.encode("utf-8")).hexdigest()[:16])
print("p28 lines:", len(src.splitlines()), "p29 lines:", len(out.splitlines()))
assert len(src.splitlines()) == len(out.splitlines()), "line count changed"

# report the new example lengths
import re, json as J
for m in re.finditer(r'"understanding":"((?:[^"\\]|\\.)*)"', out):
    s = J.loads('"%s"' % m.group(1))
    if s:
        print("%3d | %s" % (len(s), s))
