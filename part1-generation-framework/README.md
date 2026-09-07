# 第一部分：生成框架与 Prompt 实验

**当前结论：Prompt 仍未通过全维度验收；技术服务已实现并接入产品 Demo 代码，通过本地联调，公共站点尚未启用新结构。** 第一轮 p13 和语言结论是历史快照。

先看 [最新进度报告](delivery/06-第二轮进展.md)。其他 agent 从 [HANDOFF](studies/round2/HANDOFF.md) 接手，内含恢复命令、预算、失败记录及下一步计划；当前没有后台付费评测。

| 位置 | 内容 |
|---|---|
| [delivery](delivery/README.md) | 集中的汇报入口；06 为当前状态，01—05 与 p13 为第一轮快照 |
| [studies/round2](studies/round2/README.md) | 当前 A/B、消融、语言交叉、独立评审、原始响应与接手计划 |
| [runtime](runtime/README.md) | 技术结构、可启动服务、约束与执行模块、Demo SDK 和测试 |
| [eval](eval/README.md) | 第一轮冻结源码、题集、版本、实验和原始响应；禁止覆盖 |
| [notes/inputs](notes/inputs/) | 能力表原始材料 |
| [archive](archive/README.md) | 旧报告、旧计划、旧设计与回放原型 |

完整产品方案见 [PRD v17](../docs/README.md)，产品源码见 [scene-studio-demo](https://github.com/hadan8977/scene-studio-demo)。通过服务端配置启用新运行结构；未配置时仍走旧 p13 链路，不能把旧站点展示当成本轮端到端验收。

只看当前进度无需翻阅 archive 或逐个猜测 Prompt 版本号；候选选择依据和未通过项均在交接入口中。旧文件名中的 final 不代表当前推荐。
