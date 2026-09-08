"""Output-contract field length limits, switchable by round.

Round two used understanding 80, name 10, say 15. The user judged the 80-character
understanding cap unreasonable for the product on 2026-09-08, so round three relaxes
it. Old rounds keep reproducing under the old numbers by leaving SCENE_CONTRACT unset.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRESETS = {
    "v3": {"understanding": 80, "name": 10, "say": 30},
    "v4": {"understanding": 120, "name": 14, "say": 30},
}
# Round two ran with say 15; keep that exact value as the default preset.
PRESETS["v3"]["say"] = 15


def limits():
    name = os.environ.get("SCENE_CONTRACT", "v3")
    if name in PRESETS:
        return dict(PRESETS[name])
    return json.loads(Path(name).read_text(encoding="utf-8"))


LIMITS = limits()
UNDERSTANDING_MAX = LIMITS["understanding"]
NAME_MAX = LIMITS["name"]
SAY_MAX = LIMITS["say"]
SCHEMA_FILE = "schema.json" if os.environ.get("SCENE_CONTRACT", "v3") == "v3" else "schema_v4.json"

# 能力表切换：SCENE_CAPS=r3 用第三轮按删除线口径重建的表，默认沿用旧表以保证前两轮可复现
CAPS_SET = os.environ.get("SCENE_CAPS", "base")
VOCAB_FILE = "vocab_r3.json" if CAPS_SET == "r3" else "vocab.json"
CAPS_FILE = "capabilities_r3.json" if CAPS_SET == "r3" else "capabilities.json"
