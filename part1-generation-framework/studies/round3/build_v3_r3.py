"""v3_r3: the p3-generation baseline carrying the identical round-three capability table."""
import hashlib, json, os, re, sys
from pathlib import Path
os.environ["SCENE_CAPS"] = "r3"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
import contract_limits as CL
V = json.loads((ROOT / "eval" / CL.VOCAB_FILE).read_text(encoding="utf-8"))

s = (ROOT / "studies/round3/prompts/v3_c4.md").read_text(encoding="utf-8")
out = s
EDITS = [
 # the four door actions are struck in the source workbook: the whole action line goes
 ("门：左前门（规划中）（开启/关闭）、右前门（规划中）（开启/关闭）、左后门（规划中）（开启/关闭）、右后门（规划中）（开启/关闭）\n", ""),
 # massage modes are struck: only 关闭 survives
 ("主驾座椅按摩模式（规划中）（关闭/波浪/猫步/蛇形/肩部/腰部）", "主驾座椅按摩模式（关闭）"),
 ("副驾座椅按摩模式（规划中）（关闭/波浪/猫步/蛇形/肩部/腰部）", "副驾座椅按摩模式（关闭）"),
 ("规划中或提议动作写进warnings时必须包含完整能力名，例如[\"音乐播放：尚未上线，仅供提议\"]。",
  "能力表里的每一条都同等可用，不分上线状态，不需要为任何一条在warnings里加成熟度说明。"),
 ("## 条件能力表（注册表版本 2026-09-07.0807）", "## 条件能力表（注册表版本 2026-09-08.r3）"),
]
for old, new in EDITS:
    n = out.count(old)
    assert n == 1, ("edit missing or ambiguous", old[:44], n)
    out = out.replace(old, new)
# every maturity tag disappears; the tiers no longer exist
out = out.replace("（规划中）", "").replace("（提议，需共建）", "")
assert "规划中" not in out and "提议，需共建" not in out

# parse the resulting tables back out and require them to equal the harness table
def names_in(section):
    found = set()
    for line in section.splitlines():
        if "：" not in line: continue
        for chunk in line.split("：", 1)[1].split("、"):
            m = re.match(r"^([^（(]+)", chunk.strip())
            if m and m.group(1).strip(): found.add(m.group(1).strip())
    return found
cond_sec = out.split("## 条件能力表", 1)[1].split("## 动作能力表", 1)[0]
act_sec = out.split("## 动作能力表", 1)[1].split("\n## ", 1)[0]
for kind, sec in (("conditions", cond_sec), ("actions", act_sec)):
    got, want = names_in(sec), set(V[kind])
    assert got == want, (kind, "缺:", sorted(want - got), "多:", sorted(got - want))

dst = ROOT / "studies/round3/prompts/v3_r3.md"
dst.write_text(out, encoding="utf-8")
print("v3_r3 ->", hashlib.sha256(out.encode()).hexdigest()[:16],
      "| conditions", len(V["conditions"]), "actions", len(V["actions"]),
      "| lines %d -> %d" % (len(s.splitlines()), len(out.splitlines())))
