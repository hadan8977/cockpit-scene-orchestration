# eval

场景编排模型评测套件。方法、指标、题集设计与运行命令见 `../docs/06-模型评测-速度准确率质量-方案与现状.md`。

- `build_testset.py`：题集唯一来源，改题后重跑生成 `testset.jsonl`（74 题，每题中英两版：动作 16、精准 18、模糊 10、情感 10、鲁棒 12、注入 8）。
- `vocab.json`：从同事 demo 原样抽取的能力表（35 条件、38 动作）、安全禁止项、P2 扩展能力（音乐播放、音量）。
- `prompts/p0_original.md`：同事原版；`p1_cleaned.md`：修正 schema；`p2_affect.md`：五类意图，含情绪场景、用户档案上下文、say 与 offer 字段。
- `run_eval.py`：OpenAI 兼容接口调用、流式时延、打分、汇总。`--mock` 离线自检。
- `registry.py` 与 `capabilities.json`：能力注册表，热更新的唯一来源；`registry.py render` 生成 `prompts/p3_grammar.generated.md`，`registry.py schema` 生成约束解码用的 `schema.json`，`disable/enable` 下线或恢复能力。
- `validator.py`：外部验证器，模型提议脚本裁决；读注册表状态，已下线能力直接丢弃。
- `presets.json`：十二个情绪预设，只用于离线兜底与坍缩率计算。
- `results/`：每次运行一个目录，含 `raw.jsonl`、`summary.md`、`summary.json`。

状态（2026-09-07 晚）：注册表改为从公司 2026-07 原子能力表导入（`import_capabilities.py` → `vocab.json` v2 → `capabilities.json`，96 条带成熟度；旧表 `vocab_v1.json` 给 p0 到 p2 用）；题集 126 题 12 类（新增 N 类 12 题）；验证器加成熟度档位。

状态（2026-09-07 午）：题集扩到 114 题 11 类（新增弱意图 F、记忆 G、观察 H、追问 I、显式创建 J）；注册表加条件语义层 5 条；harness 支持 `--model-key`（models.json 多供应商）、`--response-format json_schema`、理解句出齐时延、relevance 区间、记忆期望；新增 `run_matrix.py` 批跑与对比、`judge.py` 机器评审、`blind_pack.py` 盲评打包、`export_cases.py` 原型回放数据。Kimi K2.7 冒烟 32 句通过 81%。计划见 `../docs/第一部分-测试计划-生成框架与选型-v1.md`。

旧状态（2026-09-02）：离线自检 P2 全部 66 题通过；P0 与 P1 风格下情感题里离不开音乐的几题按预期失败（原能力表没有音乐）。尚未对真实模型运行，等 dsv4flash 的 key。

真跑：
```bash
export EVAL_BASE_URL=https://api.deepseek.com EVAL_API_KEY=sk-xxx EVAL_MODEL=deepseek-v4-flash
python3 run_eval.py --prompt prompts/p2_affect.md --thinking off --repeat 3 --tag v4flash-p2-nothink
python3 run_eval.py --prompt prompts/p0_original.md --thinking off --repeat 3 --tag v4flash-p0-nothink
```
