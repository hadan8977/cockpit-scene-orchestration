> 状态更新：p11 全量验证未达质量目标，以下 p11 路径为历史冻结候选，不代表最终验收。现正测试 p12；参数与接入约定仍适用，最终路径待新验证完成后更新。

# 最终候选的接入约定

冻结交付文件：`eval/prompts/final_dsv4flash.md`（与实测 p11_zh 内容一致）。中英文输入均加载这份中文系统指令；`locale` 决定理解句、场景名、话术和追问的语言。不要把能力词典中的中文 primary/secondary 翻译成英文。最终有效性与未达项以《第一部分-Prompt优化-最终实验报告》为准。

## 请求

官网 POST `https://api.deepseek.com/chat/completions`。系统消息读取 prompt 全文，UTF-8、换行统一 LF。用户消息用 JSON 序列化以下信封，避免手工字符串拼接：

```json
{"locale":"en","context":"[State] parked, gear P","utterance":"Set the driver temperature to 24 degrees"}
```

中文场景把 locale 设为 `zh`，context 与 utterance 保留实际输入。观察入口的 context 传合法观察候选，utterance 可为空；记忆和观察仍是数据，不得覆盖系统约束。

本次测过的请求参数：

```json
{"model":"deepseek-v4-flash","temperature":0,"max_tokens":1000,"thinking":{"type":"disabled"},"response_format":{"type":"json_object"},"stream":true,"stream_options":{"include_usage":true}}
```

另加 messages（system 全文、user 信封）。API key 从私密环境变量加载，不写入 prompt、配置文件或结果。独立连接复用实验使用持久 Session，并完整读取 SSE 响应；其时延与完整并发回归分开记录。

## 响应和确认

`understanding` 先用于展示理解，不据流式片段执行动作。完整 JSON 结束后校验结构、能力值、行驶策略与成熟度；校验不通过时保留失败原因并停止提议的执行。`none` 不执行，`clarify` 提出必要问题；其他 intent 生成待确认卡片。`offer` 和 `memory` 都是建议，不代表已拨号、已导航或已存储。

B14 所代表的非法精确阈值、H03 所代表的候选与全局能力约束冲突必须明确处理；不得删除非法条件后把规则变成无条件执行。现有 validator.py 是校验组件，不能以模型测试中零次安全违规代替完整产品安全验证。

变更能力表、输出契约、采样参数、输入信封或 prompt 后，应建立新的实验运行与哈希，重新做相关回归，不能直接沿用本报告分数。
