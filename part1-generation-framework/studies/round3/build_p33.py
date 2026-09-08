"""p33 = p31 targeted at the experience gap the blind review exposed.

Diagnosis from the judges' own losing cases: the candidate loses grounding and wording almost entirely
where it declines to act — it clarifies a threshold that is already on the grid, stores a negative
preference as memory without switching the device off, or answers a complete request with a telegraphic
say. Three edits, all aimed at that.
"""
import hashlib
from pathlib import Path
src = Path("prompts/p31_zh.md").read_text(encoding="utf-8")
R = [
 # 1. 只有真的不在刻度上才追问；在刻度上就直接做
 ("精确阈值不满足步长必须追问，不擅自取整。",
  "精确阈值先按能力表的步长算一遍：能被步长整除就直接用，不要追问，也不要声称它不合法；"
  "只有真的落在两个刻度之间才追问。车内PM2.5步长10，所以85要问，而80、120、150都是合法值，直接用。"),
 # 2. 否定偏好与确认句要落到当前状态
 ("11. 提神、清醒、透气类目标的风量不超过2挡，优先通风与换气；不要用3挡风量制造存在感。",
  "11. 提神、清醒、透气类目标的风量不超过2挡，优先通风与换气；不要用3挡风量制造存在感。\n"
  "12. 用户说出长期的否定偏好或确认某个设置时，除了记忆，还要把当前状态一并落到actions里，不能只记不做。"
  "‘以后都不想闻到香氛’要写memory并且写香氛开关=关闭；‘我不喜欢强风’要写memory并且把风量降下来。"
  "只记不做等于没有回应他此刻的要求。\n"
  "13. 能做就做，不要用追问代替判断。只有缺了它就无法生成合法卡片的信息才追问："
  "缺席位、缺日期区间、缺当前值的相对调节、目标设备不支持。其余情况按能力表给出最合理的一组动作。"),
 # 3. say 说完整一句；英文按显示宽度对齐
 ("英文say若需要，选≤30字符的自然短句，逐字符核对。",
  "say要说完整的一句话，承接用户的处境并点名这次真正写进actions的动作或取值，读起来像人说的，"
  "不要写成‘风量1挡，温度26℃’这样的电报体。中文≤30字符；英文是半角字符，按同样的卡片宽度折算为≤60字符。"
  "例如‘好，风量降到1挡，温度设到26度’、‘Purification will turn on above 120’。"),
 ("；≤30字符（含英文空格），如‘座椅热到2挡了’、‘灯调到20%，音乐也开了’、‘Seat warm at 2, light down’。",
  "；说完整的一句，读起来像人说的，不要电报体。中文≤30字符，英文是半角字符，按同样卡片宽度折算为≤60字符。"
  "如‘好，座椅热到2挡了’、‘灯调到20%，音乐也开了’、‘Seat heating is on at level 2 now’。"),
]
out = src
for old, new in R:
    assert out.count(old) == 1, ("missing", old[:46], out.count(old))
    out = out.replace(old, new)
Path("prompts/p33_zh.md").write_text(out, encoding="utf-8")
print("edits", len(R), "| p33", hashlib.sha256(out.encode()).hexdigest()[:16], "| lines", len(src.splitlines()), "->", len(out.splitlines()))
