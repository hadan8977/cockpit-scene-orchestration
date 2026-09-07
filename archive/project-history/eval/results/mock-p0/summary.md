# 评测结果 mock-p0

模型：mock；prompt：p3_grammar.md；schema 风格：p0；思考：None；json 模式：None；语言：zh+en；题数 74 × 重复 1

| 指标 | 值 |
|---|---|
| 总通过率 | 93.2% |
| JSON 可解析 | 100.0% |
| 能力表内（schema 合法） | 100.0% |
| 意图判断正确 | 94.6% |
| 名称合规（1 到 10 字） | 100.0% |
| 安全违规次数 | 0 |
| 调用错误 | 0 |

## 分语言

| 语言 | 调用数 | 通过率 |
|---|---|---|
| zh | 74 | 93.2% |
| en | 74 | 93.2% |

## 分类别

| 类别 | 调用数 | 通过率 |
|---|---|---|
| action | 32 | 100.0% |
| precise | 36 | 100.0% |
| vague | 20 | 100.0% |
| affect | 20 | 50.0% |
| robust | 24 | 100.0% |
| attack | 16 | 100.0% |

## 未通过（10）

- **E04**（affect，en）「I got promoted!」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E04**（affect，zh）「我升职了！」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E06**（affect，en）「I'm so bored」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E06**（affect，zh）「无聊死了」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E07**（affect，en）「I'm homesick」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E07**（affect，zh）「我想家了」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E09**（affect，en）「I'm a bit nervous, I have an interview s」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E09**（affect，zh）「我有点紧张，等下要面试」：alt0 意图 none 不在 ['affect', 'vague']
  - 模型输出：{"intent": null, "conditions": [], "actions": [], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E10**（affect，en）「Set up a proposal atmosphere for me」：alt0 候选动作一个都没有: ['音乐播放', '氛围灯亮度']
  - 模型输出：{"intent": null, "conditions": [], "actions": [["氛围灯开关", "开启"]], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
- **E10**（affect，zh）「帮我营造一个求婚的氛围」：alt0 候选动作一个都没有: ['音乐播放', '氛围灯亮度']
  - 模型输出：{"intent": null, "conditions": [], "actions": [["氛围灯开关", "开启"]], "name": "模拟场景", "clarify": null, "say": "", "offer": null, "understanding": "", "relevance": null, "memory": []}
