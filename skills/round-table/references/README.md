# Round Table 参考文档

> Orchestrator 按需加载，不要一次性读取所有文档。

## 核心原则

1. **多 runtime 多样性**：claude/codex/pi 各自的 system prompt 构成架构级认知差异
2. **共享上下文**：所有参与者通过 CLI 获取同一份上下文，保持讨论连贯
3. **用户始终有控制权**：每轮结束后用户决定方向

## 文档索引

| 场景 | 文档 | 加载时机 |
|------|------|----------|
| 需要选角色 | [roles.md](roles.md) | 启动时 |
| 需要构建 prompt | [prompt-templates.md](prompt-templates.md) | 每轮构建 prompt 时 |
| 需要理解详细流程 | [discussion-flow.md](discussion-flow.md) | 进入每轮循环前 |
