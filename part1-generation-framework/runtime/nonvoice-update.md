# Scene Studio v21 的非语音入口适配

本次以 `e0e2c1b` 为基线，备份标签 `backup/product-nonvoice-e0e2c1b`。不修改交付 Prompt 或实验结论。

- 校验器允许合法「延时」之后，同一能力以不同值再次出现；同阶段的重复仍拒绝。产品 Demo 的 TypeScript 校验器同步更新。
- `confirm` 支持可选布尔 `trial`，产品传 `false`，按场景序列立即开始。省略时保持原有 3 秒试演策略，既有技术测试兼容。
- `POST /simulation/manual` 接收 `values` 和 `driving`。明确的手动车控经过能力与行驶策略校验，接管对应设备，取消该设备的未执行段，并保留手动新值供撤销时使用。
- `POST /simulation/trigger` 支持 `trial`、`new_trip`。显式新出行取消遗留任务并重新启用条件边沿；持续为真不重复触发。已关闭或删除的场景由 `/demo/context` 的权威模拟快照移除。
- 对有延时的已有场景，`modify` 保存完整校验后的阶段序列，不使用按设备名字典合并。`extend` 不得默默压平分阶段动作。
- `/state` 返回当前 `registry_revision`，供产品代理持有执行引用。到段复查仍使用当前注册表、车况与上下文。

产品端观察使用现有 `source: observation`，附结构化动作、条件和明确标注的示例证据。产品侧额外检查证据/额度/隐私及阶段保存价值，AI 的动作变更不能代替选定快照。没有新增长期自动观察挖掘或真实车辆执行。

验证：`python -m unittest discover -s part1-generation-framework/runtime -p "test_*.py" -q`，36 项通过。Scene Studio 的 `test:runtime` 另外通过实际 HTTP 服务验证代理与执行链路；provider 为 `offline_fixture`，不构成真实模型验收。
