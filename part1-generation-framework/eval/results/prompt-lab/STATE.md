# prompt 实验室进度（唯一进度真相）

最后更新：2026-09-07 09:10

## 口径
- 模型：DeepSeek V4 Flash（`--model-key ds-v4-flash`，`--thinking off`，temperature 0），微信代理端点 chatapi.weixin.qq.com，时延只作相对比较。
- 题集：`eval/testset.jsonl` 134 题中英各一版 268 句，11 类。核心子集 `eval/testset_core.jsonl` 63 题 126 句，由 `make_subset.py` 按类别等距抽取（attack 与 clarify 取满），迭代与消融单轮用它。
- 注册表 114 条，版本 2026-09-07.0807；模板 `eval/prompts/p3_template.md`。
- 上一会话的 `results/prompt-lab/00-v3` 是 126 题旧题集的结果，作废。

## 端点变更（2026-09-07 09:05）：改用 DeepSeek 官网端点
- 主端点 `--model-key ds-v4-flash-official`（api.deepseek.com，model id deepseek-v4-flash），key 在 `.env.local` 的 `DEEPSEEK_OFFICIAL_API_KEY`。
- 没有 5 小时窗口配额，并发 4 时一遍 268 句约 3 到 5 分钟，p50 约 1.6 秒，首字约 0.8 秒，理解句出齐约 1.1 秒。时延数字从此有参考价值，报告里以官网端点为准。
- 前缀缓存生效：prompt 4703 token 里 4608 命中缓存（98%），单次调用估算约 0.001 元。
- 微信代理 `--model-key ds-v4-flash` 只作备份，它的 1200 次 / 5 小时窗口配额记录留在下面。
- 费用是硬约束，见本文件「费用」一节；余额低于 3 元要停下来报告。

## 备份端点的配额（2026-09-07 09:00 发现，微信代理才有）
微信代理端点是 **1200 次 / 5 小时滑动窗口**，另有并发上限 6（`period request limit: window=5h requests=1214 effective_max=1200`、`concurrent limit exceeded: running=6 max=6`）。
- 后果：00-v0 那次 804 次调用有 277 次撞 429 被记成判分失败，原始 summary.json 的分数不可用，改用 `summary_noerr.md`（剔除端点错误后重算，判分逻辑未改）。
- 已修 harness（`run_eval.py`，备份 `run_eval.py.bak-before-ratelimit`）：429 分两种重试，period 配额墙退避 45 秒最多 40 次，concurrent 退避 3 秒最多 10 次；新增环境变量 `EVAL_MIN_INTERVAL` 全局最小请求间隔。
- **今后每次跑 DeepSeek 都要带 `EVAL_MIN_INTERVAL=15`**（4 次/分钟，正好压在 1200/5h 以内），命令形如：
  `cd eval && source .env.local && EVAL_MIN_INTERVAL=15 python3 run_eval.py ...`
- 换算：126 句子集单遍约 32 分钟；268 句全集单遍约 67 分钟；268 句三遍约 3.4 小时。

## 已完成

| 轮 | 版本 | 结果目录 | 结论 |
|---|---|---|---|
| 00 | v0 原版 p0_original | results/prompt-lab/00-v0 | 官网端点重跑中（微信代理那次 277 次调用错误，已作废删除） |
| 01 | v3 当前版 | results/prompt-lab/01-v3 | 排队中 |

上一会话 126 题旧题集的 v3 结果挪到 `results/prompt-lab/zz-stale-00-v3-126题旧题集`，只作参考。

## 当前最优版本
暂无（v3 干净基线还没跑）。候选模板 `prompts/p3_template.md`（v3）。

## 下一步（按序）
1. 等配额窗口滚过（08:07 起的那批 5 小时后开始释放，约 13:00 后才有较大余量），先用 1 次探针确认：`curl` 或跑 `--limit 2`。
2. 跑 v3 干净基线：全集单遍 268 句，`EVAL_MIN_INTERVAL=15`，tag `prompt-lab/01-v3`。
3. v3 评审：`python3 judge.py --tag prompt-lab/01-v3 --judge-key ds-v4-flash`。
4. 迭代按 `prompts/CHANGELOG.md` 的假设清单走，每轮只改一处，用核心子集 `--testset testset_core.jsonl`，tag `prompt-lab/NN-xxx`，版本文件 `prompts/p5_rNN_xxx.md`。已备好的单点改动（`mkprompt.py --edit`）：safety、json_stable、say_en、caps_usage、clarify_triggers、examples、anticollapse、neg_memory、caps_compact、compress、und_cap。
5. 消融 9 项、中英搭配、冻结、四模型对比。

## 评审模型口径
- 迭代与消融用 `judge.py --judge-key ds-v4-flash`（不花 OpenRouter 钱）。
- 只在最后四模型小对比时对 P-final 再用 `--judge-key qwen3.8-27b` 交叉校验。
- 报告要写明 DeepSeek 自评自判的偏差风险与两套评审分的一致性。

## 费用
- DeepSeek 官网余额起点：19.40 元（2026-09-07 09:08）。查法 `curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer $DEEPSEEK_OFFICIAL_API_KEY"`。
- 记账工具 `python3 cost.py`（追加一行到 `logs/cost_ledger.txt`）、`python3 cost.py --estimate <tag>`（按 usage 估算某次运行的花费）。
- 余额低于 3 元停止并报告。

## OpenRouter 花费
- 会话开始 total_usage = 0.042054409（2026-09-07 08:00 读数）。
- 至今未花：本会话尚未调用 OpenRouter。上限 1.5 美元。
