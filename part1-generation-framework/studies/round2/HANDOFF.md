# Agent 接手入口

更新：2026-09-08（北京时间；原始日志时间为UTC）。用户要求阶段汇报并上传全部进度。本快照**没有后台评测继续花费**；01—09生成和现有全部评审已收尾。可从GitHub重建数据和预算，不依赖本session的终端编号。

## 先读结论

**没有验收通过的P-final。** p24是当前完整开发参照，删表达块版本是下一条值得验证的路线。用户要求每个维度优于baseline，不能用分寸补偿贴切/话术/组合的下降；不要把p13、p19或p24写成已经全面胜出。数学上已到100%/0违规的维度只能保持上限，区间不支持提升就写未证实。

- 主对照：`prompts/v3_latest_compatible.md`；补充对照：`prompts/v0_latest_protocol_compatible.md`。都使用当前114能力，v0做过语法和接口适配，不能称逐字原版。
- 最新完整开发参照：[p24中文](prompts/p24_zh.md)；下一路线：[删表达块](prompts/p24_without_wording.md)。p25只把相同值域/成熟度的词典项分组，自动合规略低，尚未选用。
- p24在07同批128条可用94.53%、安全0；v3为42.97%、安全2。p24 p50快，但p95略慢，不能说速度各项都赢。
- p24对v3完整盲评：Luna贴切/分寸/组合升、话术略降；Qwen贴切/话术/组合仍降。两模型各有缺失评分。见[体验评审](judge/development-p24/summary.json)及[统计推断](judge/development-p24/inference.json)。
- 表达删块vs完整p24：自动93.75% vs92.19%；Luna话术持平、其他三维微升；Qwen四维点估计升，但缺1份，多数区间含0，Holm后未证明优势。**没有证据说这块必须保留。**
- 语言交叉512次已跑：p24统一中文93.75%、统一英文91.41%、按输入分流92.97%。差异小，尚未证明一种语言在所有维度最好；英文方案语言合规略高。结论只适用于这些译文/示例组合，删块路线不能沿用。
- 新留出[80题v2.1](holdout-v2.1.jsonl)已冻结，**模型调用0次**。是本代理编写的新题，非独立人工基准；v2.1仅改了两处离线金标准错误，v2仍保留。首调以后不能用来优化同一候选。

面向用户的汇报见[当前进度报告](../../delivery/06-第二轮进展.md)；机器状态见[STATE.json](STATE.json)；下一步的资源分配和门槛见[接手计划修订](AMENDMENT-08-HANDOFF.md)。

## 代码和仓库

| 内容 | 位置 |
|---|---|
| 实验、PRD、技术服务 | `hadan8977/cockpit-scene-orchestration`，本目录属于`part1-generation-framework/studies/round2` |
| 产品Demo | [hadan8977/scene-studio-demo](https://github.com/hadan8977/scene-studio-demo)，接入提交`0ad75616f80610d82987a46ef37867edc74e6996` |
| 当前Windows框架checkout | `D:\PaseoWorkspace\hadan\work\framework-audit-474f662` |
| 产品隔离checkout | `D:\PaseoWorkspace\hadan\work\scene-runtime-integration`；不要覆盖另一个session的`outputs\scene-studio-public` |
| 当前可用Python | `D:\PaseoWorkspace\hadan\work\audit-python312\python.exe`；也可使用正常Python3.12+ |
| 私有凭据 | 当前机器私有`.env`/已有凭据管理；不在GitHub、不得写进报告。默认`.env`在工作区根目录，由用户既有授权使用 |

仓库根目录`D:\PaseoWorkspace\hadan`还有另一个Web项目，不是本次修改目标。不要改它的app源码。API与GitHub上传授权来自当前用户任务；接手环境若没有凭据，先读代码和证据，不重置预算后盲跑。

## 克隆后先恢复，零付费

在框架仓库根目录执行。Python需要requests、jsonschema；建议安装本目录`requirements.txt`。

```powershell
python part1-generation-framework/studies/round2/handoff.py verify
python part1-generation-framework/studies/round2/handoff.py restore
python part1-generation-framework/studies/round2/handoff.py verify
python -m unittest discover -s part1-generation-framework/runtime -p test_*.py
python tools/check_repository.py
```

`restore`验证9份生成原始响应压缩包的SHA-256，再解压为被gitignore的raw.jsonl，并从[去凭据的预算检查点](handoff-budget/manifest.json)恢复缺失的私有账本。已有raw必须同哈希，已有账本不会被覆写。评审raw.jsonl已直接跟踪。**不要在新的checkout先运行study.py或review.py再恢复账本，那会把调用次数重新从0计算。**

预算当前：DS4107/7000，剩2893；官网余额末次观测12.90元，初始17.01元，观测保底7.01元（最多下降10元且账户至少3元）。余额变化可能包含外部调用。评审528/1200，已计费用约$0.840707，总上限$2.50。腾讯/微信端点本轮0次且不要调用。每个provider同时只跑一个会写账本的进程；DS与OR分别有账本，可以各跑一个。

## 可立即执行的下一步

这两项均已在首次调用前登记，**还没有调用**。执行前先检查恢复完成、预算和当前是否有人在跑同类进程。

```powershell
# 384次DS：完整p24 / 删表达块 / v3，64题、中英、随机交错
python -u part1-generation-framework/studies/round2/study.py plans/10_wording_followup.json --env-file <私有env路径>

# 256次OR：八模块分别4题、中英、交换位置、两位评审
python -u part1-generation-framework/studies/round2/ablation_review.py run --env-file <私有env路径>
```

可先做这两项后决定路线。**后面的完整回归、最终语言确认、新留出及留出评审尚未登记具体候选，也未执行**；按修订08先冻结候选和抽样，再生成新run_id计划、提交GitHub，才发第一条请求。若开发结果仍未过体验门，先优化，不把剩余预算机械花在“确认成功”上。

现有runner支持`--max-new N`限制本次新增次数，恢复时按(id,lang,rep,variant)跳过已完成任务；失败请求也算已完成，不自动重试。manifest不匹配必须新run_id，不能修改已跑Prompt/题集/评分器后强行续跑。generation原始响应只在本地raw.jsonl，完成后自动归档raw.jsonl.gz与哈希；提交压缩归档即可，不丢失败。

## 已完成证据索引

| 阶段 | 生成数 | 状态 |
|---|---:|---|
| 01_screen | 640 | p13/v3、v0适配和两条新路线；v0早期标签不兼容单独说明，不拿5.47%作公平结论 |
| 02_refinement | 512 | p16/p17、修正接口的v3/v0；p17后来被体验评审否决 |
| 03_completion | 256 | p17/p18的路由与完整性修补 |
| 04_examples | 384 | p18/p19/p20，保留/替换示例对照 |
| 05_experience_route | 384 | p19/p21/p22；独立重建退步，p21有安全违规 |
| 06_transfer | 384 | p19/p23/v3；p23后续盲评未过 |
| 07_completeness | 384 | p23/p24/v3；完整效果、具体表达，仍未过逐维门 |
| 08_ablation | 640 | 完整+基线+八模块对照；删示例下降10.94pp，但题级区间触0，不能说已统计证明必要 |
| 09_language | 512 | p24/p25 × 中英系统指令 × 中英输入 |
| 约束接口探测 | 6 | Responses schema与strict_tool各3，均有效；严格工具更快，仅小样本 |
| 真实运行服务冒烟 | 5 | 6场景通过，其中注入在调用前拦截，故只付费5次 |

合计4107。评审528：校准16、p17/p23/p24各128、表达消融128。完整归档、summary、manifest均在`results/`与`judge/`；[analysis](analysis/)另列簇级区间、符号随机化、Holm与语言策略，不覆盖原始score。

评审的已知误读见[REVIEW_LIMITATIONS.md](judge/REVIEW_LIMITATIONS.md)。不要挑对自己有利的评审、忽略缺失或事后改变量表；新量表需另版本、校准并两臂全量重评。原134题有H03/B14等金标准冲突，N07生日亮度金标准偏窄，保留原分母并另解释。

## 运行结构与Demo完成程度

[技术服务README](../../runtime/README.md)包含架构图、接口、运行命令、演示步骤和PRD差异。已实现动态注册表→Prompt/严格Schema/验证器，可信上下文与≤300字节保守记忆包，已有场景引用，局部修改，SSE理解句，确认、保存、时间线、热更新复查、取消和恢复。只是车辆状态模拟，没有车辆RPC。

已通过Python30项、产品逻辑67项、现有界面29项、运行服务界面1项、类型检查、生产webpack构建、跨TS/Python的HTTP/SSE固定数据测试，以及真实模型6场景冒烟。真实strict_tool五次总时延2.08–2.47秒，理解句0.875–1.406秒；不能代表总体p95或达到0.6秒目标。

当前机器本地`http://127.0.0.1:3101`由本任务启动，`/api/models`已返回configured=true、Part 1 Runtime、strict_tool；它可能随进程结束而不可用，接手请先探测端口。没有可用的浏览器自动化连接，视觉走查未完成。公共Vercel站点**未启用新结构**，不能访问这台机器的localhost。默认未配置仍使用旧p13链路。

本地重新启动（先完成产品构建；旧服务占端口时不要再启动第二个）：

```powershell
node part1-generation-framework/runtime/sdk/start_demo.mjs <python路径> <产品checkout路径> <私有env路径> p24_zh.md
```

SDK只传私有token到服务端，不打印、不持久化。当前产品checkout复用另一个checkout的node_modules junction，所以Turbopack拒绝越界链接，已用`npm run build -- --webpack`验证；正常独立安装可按产品原配置构建。

未完成：最终Prompt验收、完整模型选型、最终候选新留出、公共完整结构部署、真实语音/记忆/车辆接入、完整日期/跨日额度与观察挖掘、语音训练语料和人工产品验收。含未上线动作的提案目前整体不执行，未实现更细的部分执行降级；完整差异在运行README中。不要把第一部分乃至PRD全项目标成全部完成。

## 提交与数据约束

- 旧`eval`370份实验资产、第一轮p13及其哈希保留，不改分母、不覆盖失败文件。`delivery`01—05是历史快照，最新进展看06和本文件。
- 仅提交代码、计划、报告、去凭据预算快照、虚构题集/响应、统计与哈希。不提交`.env`、API key、PAT、服务token或真实用户隐私数据。
- 每完成一阶段更新STATE、报告、计划与新证据并提交，再非强制push；fetch发现别人的新提交先整合，不覆盖其他session工作。
- 不重跑已完成实验来凑分；本快照没有待自动继续的付费任务，下一次调用需由接手agent按以上计划主动启动。
