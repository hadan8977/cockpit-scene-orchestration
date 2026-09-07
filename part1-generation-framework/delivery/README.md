# 第一部分交付与当前验收状态

> 本目录保存第一轮交付快照。根据用户新要求，已启动[第二轮逐维优化与运行架构实现](../studies/round2/README.md)；p13 不作为全方位胜出的最终版本。

**先看 [第二轮进展与当前结论](06-第二轮进展.md) 和 [可运行技术结构](../runtime/README.md)。** 当前没有逐维验收通过的最终 Prompt。下面01—05、p13与其语言策略属于第一轮快照；它们不代表新一轮已经完成。

其他 agent 请读 [接手入口与恢复命令](../studies/round2/HANDOFF.md)，接手计划和当前进度均已保存。本目录按以下用途阅读。

| 文件 | 用途 |
|---|---|
| [06 第二轮进展](06-第二轮进展.md) | 当前 Prompt、语言实验、架构和 Demo 完成程度 |
| [HANDOFF](../studies/round2/HANDOFF.md) | 最新证据索引、预算恢复、可执行计划与未完成项 |
| [01 结论与 Demo 状态](01-结论与Demo状态.md) | 两分钟了解已完成、未完成与证据范围 |
| [02 整体结构与接入边界](02-整体结构与接入边界.md) | 实验框架、Prompt、前后端和车辆模拟之间的关系 |
| [03 Prompt 实验报告](03-Prompt实验报告.md) | A/B、消融、语言交叉、留出、时延、评审与局限 |
| [04 接入说明](04-接入说明.md) | 请求信封、模型参数、流式展示和校验原则 |
| [05 进度与后续计划](05-进度与后续计划.md) | 本轮完成记录与 Demo 联调的验收清单 |
| [prompt/system-zh.md](prompt/system-zh.md) | 第一轮 p13 冻结副本；尚未通过当前全维度要求 |
| [config/request.example.json](config/request.example.json) | 本次测试过的模型参数和中英输入信封示例，无密钥 |
| [contracts](contracts/) | 本次实验使用的能力、词典及输出 schema 快照 |
| [evidence](evidence/README.md) | 全部实验、原始响应、失败记录和离线复算入口 |
| [manifest.json](manifest.json) | 交付资产的来源、版本与 SHA-256，防止混用旧版 |

第一轮 Prompt、请求示例和契约在本目录内，冻结证据在 [eval](../eval/README.md)；第二轮候选和证据在 [round2](../studies/round2/README.md)。[技术服务](../runtime/README.md)已接入独立 [scene-studio-demo](https://github.com/hadan8977/scene-studio-demo) 代码，本地通过联调；公共站点尚未启用新结构。

本目录的交付副本从冻结实验资产复制，禁止单独手改副本。变更模型输入、Prompt、参数或能力契约应开启新版本和新回归，不能沿用旧报告数字。历史 `eval/prompts/final_dsv4flash.md` 是 p11，本目录副本是第一轮 p13；第二轮没有验收通过的最终版本。
