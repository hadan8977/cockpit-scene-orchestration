# 第一部分：生成框架与云端小模型选型（2026-09-07）

对应 PRD v15 的 2.4 与 GEN_001 到 GEN_004。这个文件夹自成一体，可以单独运行。

| 内容 | 位置 |
|---|---|
| **PRD v16**：以公司 agent v13 精简版为底本重写，先说这是什么，产品与技术分章，能力表核实，demo 三部分展开（顶层 docs 也放了一份） | `docs/场景编排主动层-PRD-v16.md` / `.docx` |
| PRD v15（上一版，按评审意见与能力表更新） | `docs/场景编排主动层-最终方案-v15-PRD.md` / `.docx` |
| 能力表对照结论（解决了什么、拿走了什么、值域变化、提议三条） | `docs/能力表对照-2026-07版-结论与改动.md` |
| 测试计划 v1.2（含用户最终定的 OpenRouter 17 个模型） | `docs/第一部分-测试计划-生成框架与选型-v1.md` |
| Figma Make 提示词：概念舱场景原型 v2（视觉与人体工学） | `docs/FigmaMake提示词-概念舱场景原型-v2.md` |
| 设计 prompt v1：场景 app 单页 | `docs/原型设计prompt-场景app一句话生成.md` |
| 评测套件：126 题中英、注册表 96 条（公司能力表导入，含成熟度）、prompt、验证器、harness | `eval/` |
| 能力表导入脚本与原始表 | `eval/import_capabilities.py`、`notes/inputs/` |
| 模型候选清单 / 批跑 / 机器评审 / 盲评打包 / 原型回放导出 | `eval/models.json`、`run_matrix.py`、`judge.py`、`blind_pack.py`、`export_cases.py` |
| Kimi K2.7 冒烟结果（32 句，通过 81%） | `eval/results/smoke-kimi-k27-p3-zh/` |
| 原型 v1（单页，回放真实输出）与概念舱布局草稿（未完成，只作参考） | `demo/gen-app/`、`demo/cockpit/` |
| Markdown 转 docx | `tools/md2docx.py` |

跑评测（key 到位后）：

```bash
cd eval
export DEEPSEEK_API_KEY=... OPENROUTER_API_KEY=...
python3 run_matrix.py --check
python3 run_matrix.py --role 主候选 --prompts p3 --thinking off --judge --judge-key ds-v4-flash
```

能力表更新后重建注册表：

```bash
cd eval && python3 import_capabilities.py && python3 registry.py build && python3 registry.py render && python3 registry.py schema && python3 build_testset.py && python3 run_eval.py --mock
```
