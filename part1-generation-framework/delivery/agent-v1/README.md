# 场景 Agent v1 —— 第一部分交付包

一句话输入 → 结构化场景提案。**不是只有一个 prompt**：prompt 只负责生成，
真正保证「下发到车上能执行」的是它外面那四层门控。这个包把五层全部装齐，可独立启动。

定版 `p36`，哈希 `cffcda9a8f58…`，冻结记录见 `FINAL-p36.json`（含全部文件哈希）。

---

## 1. 五层结构

```
用户一句话
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ ① 上下文组装  context.py                             │
│    已确认记忆 · 当前车况 · 已有场景摘要（最多 3 条）      │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ ② 能力注册表  registry/capabilities.json  ← 单一事实源 │
│    114 条能力，条件 64 / 动作 72，含值域与禁止值        │
│    同一份快照同时渲染下面三样，三者永远一致：             │
│      · Prompt 的能力段（compile_prompt）              │
│      · 严格工具 Schema（strict_tool_schema）          │
│      · 外部验证器的白名单（core.validate）             │
└─────────────────────────────────────────────────────┘
    │                    │                    │
    ▼                    ▼                    ▼
┌──────────┐   ┌──────────────┐   ┌──────────────────┐
│③ Prompt  │   │④ 约束解码     │   │⑤ 外部验证         │
│ p36_zh.md│──▶│ provider.py  │──▶│ core.validate    │
│          │   │ strict_tool  │   │ output_contract  │
└──────────┘   └──────────────┘   └──────────────────┘
                                          │
                                          ▼
                              ┌──────────────────────┐
                              │⑥ 执行策略 scheduler   │
                              │ 显式确认 · 试演 · 快照 │
                              │ 撤销 · 仲裁 · 日志     │
                              └──────────────────────┘
```

**为什么解码约束之后还要外部验证**：约束解码只能保证「字段类型和枚举合法」，
保证不了「行驶中车窗不超过 20%」「唯一条件与动作不能是同一能力的相反状态」
「攻击句不能输出任何动作」这类**语义与安全**规则。这些必须在模型之外判。

---

## 2. 目录

| 路径 | 是什么 | 谁在用 |
|---|---|---|
| `prompt/p36_zh.md` | 定版 prompt，285 行。能力表段由注册表渲染，其余为规则与 29 条示例 | ③ |
| `registry/capabilities.json` | 114 条能力，含 `cond_values` / `act_values` / `deny_act_values` / `class`（安全等级） | ② |
| `registry/vocab.json` | 校验器用的扁平词表，与上表同源 | ⑤ |
| `contract/scene.schema.json` | 输出 JSON Schema，`additionalProperties:false`，逐字段 maxLength 与枚举 | ④⑤ |
| `gates/output_contract.py` | 契约校验 + 策略违规（安全、成熟度、攻击、记忆纪律） | ⑤ |
| `gates/contract_limits.py` | 字段长度上限，按语言折算 | ④⑤ |
| `runtime/core.py` | 注册表、Schema 生成、prompt 编译、`validate` 主验证器 | ②③⑤ |
| `runtime/provider.py` | 模型调用，`strict_tool` 模式，唯一工具 `propose_scene` | ④ |
| `runtime/scheduler.py` | 执行策略：提案有效期、显式确认、试演、快照、撤销、仲裁 | ⑥ |
| `runtime/context.py` | 可信上下文组装 | ① |
| `runtime/server.py` | HTTP 服务，产品 Demo 从服务端路由调用 | 全部 |

---

## 3. 输出契约

```json
{"understanding":"","relevance":0,"intent":"none","name":"","logic":"AND",
 "conditions":[],"actions":[],"say":"",
 "offer":{"type":"none","target":""},
 "memory":[],"unsupported":[],"warnings":[],"clarify":null}
```

| 字段 | 约束 |
|---|---|
| `understanding` | 中文 ≤120 字符，英文 ≤200 字符（半角按同样卡片宽度折算） |
| `name` | 中文 2–5 字，英文 ≤14 字符 |
| `say` | 中文 ≤30 字符，英文 ≤60 字符 |
| `intent` | `action` / `precise` / `vague` / `affect` / `observation` / `clarify` / `none` |
| `conditions[].primary` | 必须在注册表的 64 条条件能力内 |
| `actions[].primary` | 必须在注册表的 72 条动作能力内 |
| `*.secondary` | 必须逐字匹配该能力的值域；区间型要带单位并满足步长 |
| `offer.type` | `call` / `navigate` / `message` / `none` |
| `memory[].type` | `preference` / `relationship` / `place` / `dislike` |

---

## 4. 硬约束清单（不可协商）

| 门控 | 规则 | 实现 |
|---|---|---|
| 能力表 | primary 不在表内 → 整张卡片作废 | `core.validate` |
| 值域 | secondary 不在值域、缺单位、不满足步长 → 作废 | `core.validate` |
| 行车安全 | 行驶中车窗开度 > 20% → 违规 | `driving_issue` |
| 法规 | 低速行人警报音不允许被场景关闭（欧盟 R138 / 美国 FMVSS 141） | `deny_act_values` |
| 注入防护 | 「维修模式 / 限制已解除 / 忽略前面的规则 / 我是工程师」等抬权说法 → `actions`、`memory`、`offer` 全空，理解句留空，**不给降级折中值** | prompt `[safety]` + `policy_violations` |
| 意图一致 | `intent` 为 `none` / `clarify` 时 `actions` 必须为空 | `policy_violations` |
| 记忆纪律 | 第三方投毒不写记忆；第一人称事实可写 | `policy_violations` |
| 逻辑自洽 | 同一 primary 不能出现两个值；唯一条件与动作不能是同一能力的相反状态 | `global_checks` |
| 执行前复查 | 提案 5 分钟有效；执行前用最新车况与注册表 revision 重新校验；注册表变过则拒绝旧提案 | `scheduler.py` |
| 可撤销 | 每次执行前拍快照，一句「还原」回到执行前 | `scheduler.py` |

---

## 5. 边界：什么不该进这个 Agent

按 PRD 3.5「问三，值不值得」与旅程一第 1 幕：**单动作不走场景**。
「打开主驾座椅加热」「把音量调到 40」这类纯单设备指令，应由语义理解层直接路由到**车控 Agent**，
不进场景大脑。场景要动 2 个以上元素，否则一句车控就够了。

评测题集里已按这条剔除 26 道越界题（打 `scope: car_control` 标记）。

---

## 6. 启动

```bash
pip install requests jsonschema
export SCENE_CAPS=r3 SCENE_CONTRACT=v4
python3 runtime/server.py \
  --env-file <私有环境文件> \
  --mode strict_tool \
  --template prompt/p36_zh.md
```

私有环境文件需要 `DEEPSEEK_API_KEY`（或腾讯代理的 `DEEPSEEK_BASE_URL` + key）与自行生成的 `PART1_RUNTIME_TOKEN`。
**密钥绝不入库。** 服务默认只监听 `127.0.0.1:8787`，所有接口要求 Bearer token。

主要接口：

| 方法 | 路由 | 用途 |
|---|---|---|
| POST | `/generate` | 一句话 → 场景提案（含理解句、动作、裁决、prompt 哈希） |
| POST | `/confirm` | 显式确认后执行 |
| POST | `/restore` | 一键还原到执行前快照 |
| GET | `/registry` | 当前能力表快照与 revision |
| GET | `/schema` | 当前输出 Schema |
| GET | `/state` | 模拟车况 |
| GET | `/health` | 健康检查 |

---

## 7. 这一版的实测水平

同一套能力表、同一套契约下，与同事原版（`v0_r3`）对比：

| | 开发集 123 题 × 中英 | | 留出集 50 题 × 中英 | |
|---|---:|---:|---:|---:|
| | **p36** | 原版 | **p36** | 原版 |
| 合结构 | **98.8%** | 62.2% | **99.0%** | 66.0% |
| 任务对 | **84.6%** | 40.2% | **78.0%** | 26.0% |
| 安全违规 | **0** | 16 | **0** | 5 |
| 攻击类任务对 | **100%** | 38% | — | — |

体验四维盲评（双评委、双向位置交换、Holm 校正）：8 个格子 7 个为正，
分寸两位评委都显著更好；唯一负值是同模型评委的贴切 −0.075，置信区间跨 0。

完整方法与例子见 [`../09-第一部分-测试与优化报告.md`](../09-第一部分-测试与优化报告.md)。

---

## 8. 自检：这个包自己能证明自己是自洽的

```bash
SCENE_CAPS=r3 SCENE_CONTRACT=v4 python3 verify.py
```

不发生任何模型调用。实测输出：

```
[1] 提示词与注册表
  通过 提示词哈希 == 冻结记录                cffcda9a8f58920e
  通过 下发的提示词与被评测的逐字节一致        True
  通过 能力段相对注册表无漂移                verified-in-place
  通过 注册表条数                          114
[2] 输出契约
  通过 Schema 顶层字段数                   15
  通过 禁止额外字段                        False
[3] 门控
  通过 合法卡片放行            valid=True  executable=True
  通过 关闭 AVAS 被拦          valid=False executable=False  能力枚举不合法
  通过 行驶中开窗 100% 被拦     valid=False executable=False  行驶中车窗最多20%
  通过 自造能力被拦             valid=False executable=False  能力枚举不合法
  通过 已剔除取值被拦            valid=False executable=False  能力枚举不合法
  通过 中文 say 超 30 字符被拦   valid=False executable=False  say 超长：38 字符 > 30
  通过 英文 say 39 字符放行     valid=True  executable=True
```

第三项是这次补上的一处缺口：评测脚本按语言把关 `say`／`understanding`／`name`
的长度，运行时的 `core.validate` 原先没有这道检查，一条 46 字符的中文 say
可以直接通过。两把尺子不一样，报出来的合规率就不代表线上行为，已对齐。

## 9. 接在产品 demo 上

同一份 `p36_zh.md` 与同一份能力表已接入场景 demo，线上跑的就是被评测的那一个：

| | |
|---|---|
| 线上 | https://hadan.blog/demo0908 |
| 代码 | `hadan8977/scene-studio-demo` 分支 `demo0908` |
| 模型 | DeepSeek 官网 `deepseek-v4-flash`；故障或限流回落腾讯代理，401/402 不换 |
| 校验 | `GET /demo0908/api/models` 会回报 `sha256` 与 `registryVersion`，可与本包核对 |

**为什么主用官网而不是腾讯代理**：同样的输入、同一份提示词各跑 6 次，
腾讯代理时延中位 71.8s、最大 119.6s，官网中位 1.9s，差 35 倍，并且超过
Vercel 60s 的函数上限——29 条内置用例里有 8 条直接 30 秒超时。腾讯代理
仍保留为备用（它要求模型名首字母大写，写在发布记录的 providers 段里）。

### 接入时拉齐的六处落差

demo 的外围逻辑原本是按 p13 的行为写的，换成 p36 后有六处会直接毁掉体验，
都是用真实生成把每条路径跑一遍才暴露出来的：

| # | 现象 | 原因 |
|---|---|---|
| 1 | 编辑永远失败，退回追问 | `mergeEdit` 把「say 变了」算作改了一个设备组，而 p36 每次都会重写一句话 |
| 2 | 动作上限砍掉的正是用户刚提的那一项，卡片还显示保存成功 | 新动作排在末尾，4 个上限直接砍尾巴 |
| 3 | 一句话点名两组会被反问「想先改哪一项」 | 守卫没区分「模型擅自扩大范围」和「用户自己要了两组」 |
| 4 | 补充追问答不上来，只好再问一遍 | 信封没把刚才问的那句话给模型 |
| 5 | 补充追问收到无效回答给白卡 | 模型回了 intent=none 的空卡，界面直接渲染 |
| 6 | 整条拒绝也给白卡 | p36 对攻击不复述，理解句与播报都空 |

第 1 条最典型：契约、能力表、端点都对，prompt 也是逐字节一致，但因为
p36 比 p13 更爱说话，一条与说话无关的守卫就让整个编辑路径失效。
**换 prompt 不只是换那段文本，外围每一条按旧行为写的规则都要重新验一遍。**

Web 端的门控是这套 Python 门控的等价 TypeScript 实现（`lib/contract.ts`、
`lib/agent-adapter.ts`、`lib/scene.ts`），契约数字由 `tests/contract.test.ts`
钉死在同一份发布记录上，两边不会各改各的。

## 10. 已知问题，没有掩盖

**p36 里还留着 9 处成熟度措辞**（第 36、251、253 行等），比拉平前的 44 处少，
但没有清干净。第 50 行明确写着「能力表里的每一条都同等可用，不分上线状态」，
第 253 行却还写着「同一语义有 released 条件时，不用成熟度更低的条件」——
这是**提示词内部的自相矛盾**。

它没有影响实测结果，因为交付的能力表已经把成熟度字段拉平成同一个值，
模型手上没有可依据的成熟度数据，这几行指的区分在它看到的表里并不存在。
但这是遗留的脏，不是设计。现在不改的原因是 p36 已冻结并已按这份哈希完成
全部测量与部署，改一个字就得重跑全部评测；应当在下一版一并清理。

接入 demo 时又量到两件相关的事，一并记下：

- **日期类请求会追问，且不看上下文。** 6 组日期输入做过 A/B：在上下文里
  补一行 `[Today] 2026-09-08`，结果和不补完全一样——它照样问「明天是哪一天？」。
  规则 2 写了「无当前日期却要求明天/节日/季节日期 -> clarify」，但这条并没有
  真正去读上下文里的日期。所以 demo 没有加这行，结论写在代码注释里。
- **会编能力表里没有的取值。** 「上车」这个概念在 `行程事件` 的取值里不存在
  （只有出发/到达/停车等人/离车），模型多次输出 `行程事件=上车`，被外部
  验证器拦下。这是能力表的缺口，不是模型乱来；下一版应当补上这个取值。

另外，「露营时做一个K歌场景」约六次里有一次会因为第 36 行「绝不能组合两个
未落地动作」而改成追问。这正是上面那处自相矛盾在真实交互里的样子。
