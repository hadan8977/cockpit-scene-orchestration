"""p30 = p29 with the explicit length quota removed. Length follows content, not a word count."""
import hashlib
from pathlib import Path
src = Path("prompts/p29_zh.md").read_text(encoding="utf-8")
R = [
 ("长度随请求走：单个设备的直接命令，中文15–25字、英文8–12词就够；带语境、情绪、多个设备或规则条件的请求，中文30–45字、英文12–18词。上限120字符。",
  "长度由内容决定，不设字数指标：把上面三件事说清楚需要多少字就写多少字，不凑字数也不压缩成标签。"
  "一个设备一个取值就说得清的请求，一句短话就够，不要为了显得完整而加解释；"
  "带语境、情绪、多个设备或规则条件的请求，自然会长一些。上限120字符。"),
 ("下面[examples]里每条understanding的长度就是该类请求的目标长度，照着那个密度写，不要更短。",
  "下面[examples]演示的是这三件事怎么落到句子里，照着那个写法写，不是照着字数写。"),
 # composition: state plainly that two atomic capabilities is a complete answer when that is what the goal needs
 ("通常2项，明确复杂目标可到4项；明确单控仍仅该项。",
  "通常2项，2项就把目标覆盖住了就到此为止，不要为了显得丰富再加；只有明确的复杂目标才到4项；明确单控仍仅该项。"),
 ("对于用户主动要求的氛围/放松/休息，完整覆盖2–4个互补功能",
  "对于用户主动要求的氛围/放松/休息，用2–4个互补功能覆盖目标，够了就停"),
]
out = src
for old, new in R:
    assert out.count(old) == 1, old[:50]
    out = out.replace(old, new)
Path("prompts/p30_zh.md").write_text(out, encoding="utf-8")
print("edits:", len(R), "| p30 sha256:", hashlib.sha256(out.encode()).hexdigest())
print("lines:", len(src.splitlines()), "->", len(out.splitlines()))
