# 第一部分：生成框架与云端小模型选型（2026-09-07）

对应 PRD v14 的 2.4 与 GEN_001 到 GEN_004。这个文件夹自成一体，可以单独运行。

| 内容 | 位置 |
|---|---|
| 测试计划（问题、候选、题集、双路体验门、门槛、命令、节奏、PRD 需同步的改动） | `docs/第一部分-测试计划-生成框架与选型-v1.md` |
| 原型设计 prompt（给 Figma Make / kimi） | `docs/原型设计prompt-场景app一句话生成.md` |
| 评测套件：114 题中英题集、注册表（含条件语义层）、prompt、验证器、harness | `eval/` |
| 模型候选清单（16 条，id 待 `run_matrix.py --check` 核对） | `eval/models.json` |
| 批跑与对比 / 机器评审 / 盲评打包 / 原型回放导出 | `eval/run_matrix.py`、`eval/judge.py`、`eval/blind_pack.py`、`eval/export_cases.py` |
| Kimi K2.7 冒烟结果（32 句，通过 81%） | `eval/results/smoke-kimi-k27-p3-zh/` |
| 原型页（回放真实模型输出） | `demo/gen-app/index.html` 加 `cases.json` |

看原型：

```bash
cd demo/gen-app && python3 -m http.server 8765   # 打开 http://127.0.0.1:8765/
```

跑评测（key 到位后）：

```bash
cd eval
export DEEPSEEK_API_KEY=... OPENROUTER_API_KEY=...
python3 run_matrix.py --check
python3 run_matrix.py --role 主候选 --prompts p3 --thinking off --judge --judge-key ds-v4-flash
```

顶层 `eval/` 是 9 月 3 日的版本，这里的 `eval/` 是在它之上扩展的，以这里为准。
