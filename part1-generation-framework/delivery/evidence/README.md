# 实验证据索引

最终结论以[实验报告](../03-Prompt实验报告.md)为准。本页将当前验收、早期开发与可复算材料分开；所有响应继续留在原实验路径。

| 实验 | 规模 | 证据 |
|---|---|---|
| p13 系统指令语言交叉 | 134 题 × 2 输入语言 × 2 指令语言 × 3 = 1608 次 | [05e_p13_language](../../eval/results/prompt-lab-v3/05e_p13_language/) |
| p3 / p13 A/B 与四项消融 | 32 题 × 2 语言 × 6 臂 = 384 次 | [06c_ablation](../../eval/results/prompt-lab-v3/06c_ablation/) |
| 推荐策略完整开发回归 | 从语言交叉导出 804 条，0 新增调用 | [07b_final_selected](../../eval/results/prompt-lab-v3/07b_final_selected/) |
| 冻结后独立留出 | 24 新题 × 2 语言 × 3 = 144 次 | [08_holdout](../../eval/results/prompt-lab-v3/08_holdout/) |
| 匿名模型体验评审 | 24 对；7 对缺偏好，人工未评分 | [09_blind_review](../../eval/results/prompt-lab-v3/09_blind_review/) |
| 冷连接 / 连接复用 A/B | 72 对，144 次 | [10_latency](../../eval/results/prompt-lab-v3/10_latency/) |

版本与实验设计：[最终冻结](../../eval/experiments/RELEASE_FREEZE.json)、[验收结果](../../eval/experiments/RELEASE_VALIDATION.json)、[预登记](../../eval/experiments/PREREGISTRATION.md)、[全部修订](../../eval/experiments/)、[冻结评分源代码](../../eval/experiments/frozen-source/README.md)。预登记发生时保存在本地，GitHub 后续同步，不追溯声称事先公开注册。

失败与边界：[p11 完整回归失败](../../eval/results/prompt-lab-v3/07_final/)、[p12 首轮停止](../../eval/results/prompt-lab-v3/05d_p12_language/)、[金标冲突](../../eval/experiments/GOLD_ISSUES.md)、[评审解析修订](../../eval/experiments/JUDGE-PARSER-AMENDMENT.md)。其余 p6–p12 结果均为开发/历史记录，不作为当前交付分数。

在 `part1-generation-framework/eval` 中离线核对：

```powershell
python -m pip install -r requirements.txt
python restore_raw.py
python verify_archives.py
python make_prompt_report.py
```

解压、验证和报告生成不调用模型。报告生成写入 `delivery/03-Prompt实验报告.md`。在有完整 Git 历史的仓库中，可从根目录执行 `python tools/check_repository.py` 核对迁移、链接与交付哈希；独立 ZIP 使用包内 `SHA256SUMS.json` 核对文件，响应归档仍用 `verify_archives.py` 核对。历史真实生成共 7098 次，另 1 次 HTTP 前中止预留，模型评审 24 次；完整费用口径见报告。本次目录整理新增模型调用为 0。
