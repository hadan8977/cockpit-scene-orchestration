# 本轮契约快照

以下文件与本次 p13 实验的 eval 原件内容一致，来源与 SHA-256 见[交付清单](../manifest.json)。

- [capabilities.json](capabilities.json)：能力注册表、成熟度、安全级与状态。
- [schema.json](schema.json)：输出 JSON 结构与约束。
- [vocab.json](vocab.json)：能力名称、值域与规则词典。

JSON schema 只是校验的一部分。接入还需要 [output_contract.py](../../eval/output_contract.py) 和 [validator.py](../../eval/validator.py) 中的业务约束，并完成应用执行前校验。这里没有宣称已经提供独立可上线的执行服务。
