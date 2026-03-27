# Insight Skill 参考文档

## 文档索引

| 场景 | 文档 |
|------|------|
| 理解 Insight 数据结构 | [insight-schema.md](insight-schema.md) |
| 了解提取流程细节 | [extraction-flow.md](extraction-flow.md) |
| Agent 如何消费 insight | [consumption-protocol.md](consumption-protocol.md) |

## 核心原则

1. **Behavioral Delta 是原子单位**：trigger → wrong_default → corrected_behavior
2. **双路数据管道**：显式纠正（高信噪比）优先，隐式纠正延迟处理
3. **QMD 混合检索**：BM25 关键词 + 向量语义，降级为 SQLite FTS5
4. **分层作用域**：项目级（默认）→ 通用经验提升为 user 级
5. **Agent 强制消费**：任务前检索，声明要避免的旧错误
