# 第一部分交付与当前验收状态

> 本目录保存第一轮交付快照。根据用户新要求，已启动[第二轮逐维优化与运行架构实现](../studies/round2/README.md)；p13 不作为全方位胜出的最终版本。

**先看 [第二轮进展与当前结论](06-第二轮进展.md) 和 [可运行技术结构](../runtime/README.md)。** 当前没有逐维验收通过的最终 Prompt。下面01—05、p13与其语言策略属于第一轮快照；它们不代表新一轮已经完成。

建议按下面顺序阅读，这里是本轮成果的统一入口。

| 文件 | 用途 |
|---|---|
| [01 结论与 Demo 状态](01-结论与Demo状态.md) | 两分钟了解已完成、未完成与证据范围 |
| [02 整体结构与接入边界](02-整体结构与接入边界.md) | 实验框架、Prompt、前后端和车辆模拟之间的关系 |
| [03 Prompt 实验报告](03-Prompt实验报告.md) | A/B、消融、语言交叉、留出、时延、评审与局限 |
| [04 接入说明](04-接入说明.md) | 请求信封、模型参数、流式展示和校验原则 |
| [05 进度与后续计划](05-进度与后续计划.md) | 本轮完成记录与 Demo 联调的验收清单 |
| [prompt/system-zh.md](prompt/system-zh.md) | 本轮唯一推荐的完整系统 Prompt，可直接读取 |
| [config/request.example.json](config/request.example.json) | 本次测试过的模型参数和中英输入信封示例，无密钥 |
| [contracts](contracts/) | 本次实验使用的能力、词典及输出 schema 快照 |
| [evidence](evidence/README.md) | 全部实验、原始响应、失败记录和离线复算入口 |
| [manifest.json](manifest.json) | 交付资产的来源、版本与 SHA-256，防止混用旧版 |

Prompt、请求示例和契约在本目录内；完整评测源码与响应集中在相邻 [eval](../eval/README.md)。这里不是一个可直接启动的 Web 应用。交互应用在 [scene-studio-demo](https://github.com/hadan8977/scene-studio-demo)，目前仍使用独立 Prompt 与调用链。

本目录的交付副本从冻结实验资产复制，禁止单独手改副本。变更模型输入、Prompt、参数或能力契约应开启新版本和新回归，不能沿用本报告数字。历史 `eval/prompts/final_dsv4flash.md` 是未通过完整验证的 p11，本次采用的是 **p13**。
