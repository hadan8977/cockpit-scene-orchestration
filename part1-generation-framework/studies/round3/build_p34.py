import hashlib
from pathlib import Path
src=Path("prompts/p33_zh.md").read_text(encoding="utf-8")
R=[
 ("上限120字符。","中文上限120字符；英文是半角，同样的卡片宽度折算为上限200字符，但不要为了填满而加话。"),
 ("understanding≤120、name≤14、say≤30、",
  "understanding中文≤120英文≤200、name≤14、say中文≤30英文≤60、"),
 # 已下线取值不要凭常识补
 ("先从actions字典选择primary，再逐字复制允许值。",
  "先从actions字典选择primary，再逐字复制允许值。字典里没列出的取值一律不存在，哪怕它在别的车上常见："
  "座椅按摩模式当前只有关闭一个取值，不要输出波浪、猫步、蛇形、肩部、腰部；车门不是动作能力，不能开关。"),
]
out=src
for old,new in R:
    assert out.count(old)==1,(old[:40],out.count(old))
    out=out.replace(old,new)
Path("prompts/p34_zh.md").write_text(out,encoding="utf-8")
print("p34",hashlib.sha256(out.encode()).hexdigest()[:16],"lines",len(out.splitlines()))
