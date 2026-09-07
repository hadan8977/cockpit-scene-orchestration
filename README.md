# 场景编排主动层

**最新工作：用户要求继续逐维优化并实现完整技术结构，[第二轮实验与架构工作进行中](part1-generation-framework/studies/round2/README.md)。p13 是第一轮候选，尚不满足新的逐项胜出要求。**

**第一部分当前交付在 [part1-generation-framework/delivery](part1-generation-framework/delivery/README.md)。** 先看[结论与 Demo 状态](part1-generation-framework/delivery/01-结论与Demo状态.md)，再看报告和 Prompt。

截至 2026-09-07：DS V4 Flash 的 Prompt 专项实验已完成，推荐 p13 统一中文系统指令；实验仍有未达指标。交互 Demo 在独立仓库，尚未完成这份 p13 的接入与端到端验收，不能把实验交付称为整个 Demo 完工。

| 要看什么 | 唯一入口 |
|---|---|
| 第一部分已完成的成果：结论、架构、报告、Prompt、接入参数、契约 | [第一部分交付](part1-generation-framework/delivery/README.md) |
| 第一部分还差什么、下一步顺序 | [进度与后续计划](part1-generation-framework/delivery/05-进度与后续计划.md) |
| 当前产品方案 | [PRD v17 精简版](docs/场景编排主动层-PRD-v17-精简版.md) · [详细版](docs/场景编排主动层-PRD-v17.md) |
| 可交互的 Scene Studio Demo 源码 | [独立 Demo 仓库](https://github.com/hadan8977/scene-studio-demo)；与本仓库的接入关系见[架构说明](part1-generation-framework/delivery/02-整体结构与接入边界.md) |
| A/B、消融、语言交叉、留出等实验原始证据 | [证据索引](part1-generation-framework/delivery/evidence/README.md) |
| 旧 PRD、早期报告、旧版评测与回放原型 | [历史归档](archive/README.md) |

```text
docs/                              当前 PRD v17 与配图
part1-generation-framework/
  delivery/                        本轮成果与当前状态；汇报从这里开始
  eval/                            评测源码、冻结配置、全部实验与原始证据
  notes/inputs/                    原子能力原始表与导出表
  archive/                         第一部分旧文档、旧原型、旧输入记录
archive/project-history/           仓库早期整体方案与旧评测副本
tools/                             文档生成与仓库整理校验工具
```

历史文件的版本号、结果和失败记录保留。[迁移清单](archive/file-moves-2026-09-07.json)可由旧路径查到新位置。当前推荐 Prompt 只有交付目录的 p13，旧文件名中的 `final` 不代表当前推荐。
