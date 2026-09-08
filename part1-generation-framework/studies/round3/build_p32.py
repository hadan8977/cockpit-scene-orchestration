"""p32 = p31 with the two defects the development set exposes, and nothing else.

1. Explicit single-control commands get over-expanded into sibling capabilities or the other seat.
   12 of 45 development-set failures; the rule already existed but was one clause inside another rule.
2. English say overruns the 30-character contract in the tail. 9 of 45 development-set failures.
Both are justified from the development set alone. The holdout has already been spent on p31 and is
not used to motivate or verify these edits.
"""
import hashlib
from pathlib import Path
src = Path("prompts/p31_zh.md").read_text(encoding="utf-8")
R = [
 # --- 1. single control means exactly what was named
 ("11. 提神、清醒、透气类目标的风量不超过2挡，优先通风与换气；不要用3挡风量制造存在感。",
  "11. 提神、清醒、透气类目标的风量不超过2挡，优先通风与换气；不要用3挡风量制造存在感。\n"
  "12. 用户点名了具体能力和取值时，只写他点到的那一条，不顺手补同一组里的别的属性："
  "‘香氛调到馥郁’只写香氛浓度，不加香氛类型；‘屏幕调暗’只写屏幕亮度，不加屏幕模式；‘音量调到40’只写音量，不加音效或声场。\n"
  "13. 没有点名席位的即时车控默认只做主驾，不展开到副驾或后排：‘温度调到26度’只写主驾温度控制，"
  "‘关掉座椅按摩’只写主驾座椅按摩模式，‘座椅加热开2挡’只写主驾座椅加热。"
  "只有用户说了‘前排/后排/所有/两边’或点名了某个席位，才按席位展开；‘前排’展开主驾与副驾，‘后排’展开左后与右后。"),
 # --- 2. English say has to fit, so aim below the cap
 ("say…≤30字符", "say…≤30字符"),  # placeholder, replaced below if present
]
R = [r for r in R if r[0] != r[1]]
OLD_SAY = "英文say若需要，选≤30字符的自然短句，逐字符核对。"
NEW_SAY = ("英文say目标25字符以内，硬上限30字符；写完把字符数（含空格）数一遍再输出，"
           "超了就换更短的说法，例如把‘I will announce when charging starts’改成‘I'll tell you then’。")
R.append((OLD_SAY, NEW_SAY))
out = src
for old, new in R:
    assert out.count(old) == 1, ("missing", old[:50], out.count(old))
    out = out.replace(old, new)
Path("prompts/p32_zh.md").write_text(out, encoding="utf-8")
print("edits:", len(R), "| p32 sha256:", hashlib.sha256(out.encode()).hexdigest()[:16])
print("lines:", len(src.splitlines()), "->", len(out.splitlines()))
