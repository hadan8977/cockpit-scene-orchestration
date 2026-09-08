"""p31 = p30 with the capability tables regenerated from the round-three registry, and every
maturity rule removed. Unreleased and pending capabilities are now ordinary capabilities."""
import hashlib, json, os, re, sys
from pathlib import Path
os.environ["SCENE_CAPS"] = "r3"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval")); sys.path.insert(0, str(ROOT / "runtime"))
import registry, core

reg = registry.load()
semantic = [{k: c.get(k) for k in ("id", "zh", "status", "cond_values", "act_values")} for c in reg["capabilities"]]
snapshot = {"version": reg["version"], "revision": core.digest({"generation": 0, "capabilities": semantic}),
            "capabilities": reg["capabilities"]}

src = ROOT / "studies/round3/prompts/p30_zh.md"
text, meta = core.compile_prompt(snapshot, src)

# the '*' legend and every maturity rule go away: there is no tier any more
LEGEND_C = "[CONDITIONS ONLY; * means planned/proposed/sprint ACTION requiring a named warning]"
LEGEND_A = "[ACTIONS ONLY; * means planned/proposed/sprint ACTION requiring a named warning]"
text = text.replace(LEGEND_C, "[CONDITIONS ONLY]").replace(LEGEND_A, "[ACTIONS ONLY]")
assert "*" not in "".join(l for l in text.splitlines() if " = " in l), "a star survived in the table"

DROP = [
 ("带星号*的动作每场景最多一个，warnings必须含完整能力名，例如[\"音乐播放：提议能力\"]或[\"进入情景模式：规划中\"]，不能省略。", ""),
 ("未落地能力的成熟度只在warnings里写一次，understanding和say里不重复‘尚未上线/仅供提议’，也不因此改用犹豫措辞；提议本身允许，正常说清要做什么。",
  "能力表里的每一条都同等可用，不分上线状态，不要为任何一条加成熟度说明，也不要因此改用犹豫措辞。"),
 ("有实际歌名时用播放指定音乐并标成熟度，不能退回泛泛的‘想念’；",
  "有实际歌名时用播放指定音乐，不能退回泛泛的‘想念’；"),
 ("5若用了*动作，warnings是否写了它的名字、是否超过一个；", "5"),
 ("4. 观察候选先数未落地能力：音乐播放、座椅按摩模式、进入情景模式等按星号计数，达到两个则clarify且conditions/actions=[]，请用户选择保留哪项。不能因为候选提供了动作就照单输出。一个*可保留并具名告知。",
  "4. 观察候选按它给出的条件与动作原样成卡，不因为某项能力的上线状态而拆分或追问；只有候选本身自相矛盾或超出能力表时才clarify。"),
 ("最多一个*，", ""),
 ("warnings对未落地能力统一称‘尚未上线，仅供提议’ / ‘not released; proposal only’，必须包含完整能力名，避免把sprint误称planned；其他解释随locale。记住概念提案可以选一个未落地功能并披露，不能因为怕警告而丢掉对目标最有用的手段。",
  "warnings只用于真正的限制说明（安全、越界、送达方式受限），不用于能力上线状态；其解释随locale。"),
 ("按摩模式未上线时照样写warnings。", ""),
 (" 关闭规划中能力也需要带全名的warnings。", ""),
]
for old, new in DROP:
    assert text.count(old) == 1, ("missing", old[:48], text.count(old))
    text = text.replace(old, new)
# example warnings that announced maturity are no longer valid output; safety warnings stay
text = re.sub(r'"warnings":\["[^"]*(?:尚未上线|仅供提议|not released|proposal only|planned capability|规划中)[^"]*"\]', '"warnings":[]', text)

# two examples used 主驾座椅按摩模式=波浪, a value the round-three table no longer authorises
SWAP = [
 ('{"understanding":"今天忙得累，还有十五分钟到家，座椅按上、灯调柔，最后这段路轻松些","relevance":0.6,"intent":"affect","name":"归途","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"主驾座椅按摩模式","secondary":"波浪"},{"primary":"主驾座椅按摩强度","secondary":"1挡"}],"say":"慢慢来，快到家了"',
  '{"understanding":"今天忙得累，还有十五分钟到家，灯调柔、放点放松的歌，最后这段路轻松些","relevance":0.6,"intent":"affect","name":"归途","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"音乐播放","secondary":"放松"}],"say":"慢慢来，快到家了"'),
 ('{"understanding":"累了以后可以这样搭配：座椅按轻柔的波浪档，灯光压到20%，身体先松下来","relevance":0.8,"intent":"vague","name":"歇歇","logic":"AND","conditions":[],"actions":[{"primary":"主驾座椅按摩模式","secondary":"波浪"},{"primary":"主驾座椅按摩强度","secondary":"1挡"},{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"}],"say":"可以这样搭配"',
  '{"understanding":"累了以后可以这样搭配：灯光压到20%，配一点放松的音乐，身体先松下来","relevance":0.8,"intent":"vague","name":"歇歇","logic":"AND","conditions":[],"actions":[{"primary":"氛围灯开关","secondary":"开启"},{"primary":"氛围灯亮度","secondary":"20%"},{"primary":"音乐播放","secondary":"放松"}],"say":"可以这样搭配"'),
]
for a, b in SWAP:
    assert text.count(a) == 1, ("swap missing", a[:60])
    text = text.replace(a, b)
assert not re.search(r"尚未上线|仅供提议|not released; proposal only", text), "a maturity phrase survived"

dst = ROOT / "studies/round3/prompts/p31_zh.md"
dst.write_text(text, encoding="utf-8")
info = {"candidate": "p31", "source": "p30_zh.md", "caps": "r3",
        "registry_version": reg["version"], "registry_revision": snapshot["revision"],
        "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "conditions_in_table": sum(1 for c in reg["capabilities"] if c.get("cond_values")),
        "actions_in_table": sum(1 for c in reg["capabilities"] if c.get("act_values"))}
print(json.dumps(info, ensure_ascii=False, indent=2))
