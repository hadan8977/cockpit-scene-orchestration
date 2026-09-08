# 场景编排主动层

**最新状态（2026-09-08）：第二轮已完成 4,107 次 DeepSeek 调用、528 次独立评审，尚无逐维验收通过的最终 Prompt。先看[当前进度报告](part1-generation-framework/delivery/06-第二轮进展.md)；其他 agent 从[交接入口](part1-generation-framework/studies/round2/HANDOFF.md)接手。**

**第一部分成果与状态集中在 [part1-generation-framework/delivery](part1-generation-framework/delivery/README.md)。** 其中 01—05、p13 和语言策略属于第一轮快照，06 是当前汇报。

可运行的[技术结构](part1-generation-framework/runtime/README.md)已接入独立 Demo 代码并通过本地真实模型冒烟；公共站点尚未启用新结构，最终 Prompt 与整体产品验收仍未完成。本次交接没有后台付费评测继续运行。

| 要看什么 | 唯一入口 |
|---|---|
| 第一部分已完成的成果：结论、架构、报告、Prompt、接入参数、契约 | [第一部分交付](part1-generation-framework/delivery/README.md) |
| 第一部分还差什么、下一步顺序 | [当前报告](part1-generation-framework/delivery/06-第二轮进展.md) · [接手计划](part1-generation-framework/studies/round2/AMENDMENT-08-HANDOFF.md) |
| 其他 agent 恢复数据、预算、断点并接手 | [HANDOFF](part1-generation-framework/studies/round2/HANDOFF.md) · [机器状态](part1-generation-framework/studies/round2/STATE.json) |
| 当前产品方案与评审 | [Demo 对齐修订稿与评审说明](docs/review-2026-09-08/README.md)；原方案基线：[PRD v17 精简版](docs/场景编排主动层-PRD-v17-精简版.md) · [详细版](docs/场景编排主动层-PRD-v17.md) |
| 可交互的 Scene Studio Demo 源码 | [独立 Demo 仓库](https://github.com/hadan8977/scene-studio-demo)；与本仓库的接入关系见[架构说明](part1-generation-framework/delivery/02-整体结构与接入边界.md) |
| A/B、消融、语言交叉、留出等实验原始证据 | [第二轮](part1-generation-framework/studies/round2/HANDOFF.md) · [第一轮](part1-generation-framework/delivery/evidence/README.md) |
| 旧 PRD、早期报告、旧版评测与回放原型 | [历史归档](archive/README.md) |

```text
docs/                              Demo 对齐评审稿、原 PRD v17 与配图
part1-generation-framework/
  delivery/                        本轮成果与当前状态；汇报从这里开始
  studies/round2/                   当前实验、交接、预算检查点与后续计划
  runtime/                         可运行技术服务、Demo SDK与验证
  eval/                            评测源码、冻结配置、全部实验与原始证据
  notes/inputs/                    原子能力原始表与导出表
  archive/                         第一部分旧文档、旧原型、旧输入记录
archive/project-history/           仓库早期整体方案与旧评测副本
tools/                             文档生成与仓库整理校验工具
```

历史文件的版本号、结果和失败记录保留。[迁移清单](archive/file-moves-2026-09-07.json)可由旧路径查到新位置。交付目录的 p13 是第一轮快照；第二轮尚无验收通过的最终版本，旧文件名中的 `final` 不代表当前推荐。
