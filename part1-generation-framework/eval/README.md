# 第一部分实验框架与证据

面向汇报和接入请先读 [delivery](../delivery/README.md)。本目录供复核与后续实验使用，保留原结构以维持冻结路径、哈希和配对证据。

## 当前结论

DS V4 Flash + p13 统一中文指令；134 题开发集与 24 题独立留出已完成。所有参考目标并未全部达标，详情见[最终报告](../delivery/03-Prompt实验报告.md)。实验完成不等于交互 Demo 完工，见[完成状态](../delivery/01-结论与Demo状态.md)。

| 位置 | 用途 |
|---|---|
| [prompts/final_dsv4flash_p13_zh.md](prompts/final_dsv4flash_p13_zh.md) | 推荐 p13 原件；交付目录为核对过哈希的副本 |
| [experiments/RELEASE_FREEZE.json](experiments/RELEASE_FREEZE.json) | 实测策略与冻结配置 |
| [experiments/RELEASE_VALIDATION.json](experiments/RELEASE_VALIDATION.json) | 完成项、结果及未达目标 |
| [证据索引](../delivery/evidence/README.md) | 当前 A/B、消融、语言交叉、留出、连接与体验评审 |
| [results/prompt-lab-v3](results/prompt-lab-v3/) | 本轮完整开发及验收；失败和中止记录保留 |
| [experiments/frozen-source](experiments/frozen-source/README.md) | 实验运行时的评分与调用源代码快照 |
| [prompts](prompts/README.md) | 全部历史与消融变体；不要以文件名 final 猜版本 |
| [capabilities.json](capabilities.json)、[schema.json](schema.json)、[output_contract.py](output_contract.py)、[validator.py](validator.py) | 能力与校验组件 |

## 离线复核

在本目录执行（不调用模型）：

```powershell
python -m pip install -r requirements.txt
python restore_raw.py
python verify_archives.py
python make_prompt_report.py
```

报告生成到 delivery/03-Prompt实验报告.md。打包在仓库暂存清单更新后执行：

```powershell
python package_release.py --out /your/output/prompt-study.zip
```

## 后续新增调用

实际生成入口为 safe_eval.py，旧 run_eval.py 与矩阵命令不能绕过预算直接续跑。腾讯/微信端点本轮禁用。任何 Prompt、题集、参数、评分或输入契约修改须新建运行与明确预算，不能追加进旧冻结实验；旧活动上限不直接复用。

旧 README 中 74/114/126 题、Kimi 冒烟与历史真跑命令保存在 [archive](../archive/eval-README-before-reorganization.md)，仅供追溯。
