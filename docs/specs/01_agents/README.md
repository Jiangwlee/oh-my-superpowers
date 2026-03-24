# Pi Agents 开发规范索引

开发 Agent 前读本文件。只有需要深入 Pi 框架细节时，才读详细文档。

## 核心原则

1. **Agent 必须有身份。** 无法映射到明确角色（职业/职能）的需求，应降级为 Skill。
2. **Agent 通过 Skill 调用能力。** 不在 Agent system prompt 里写裸脚本路径。
3. **约束通过模板，不通过指令。** 输出格式用模板结构约束，比用自然语言指令更可靠。
4. **工具集最小化。** `tools:` 字段只列 Agent 真正需要的工具。

## Agent 文件格式（Pi frontmatter）

```markdown
---
name: agent-name
description: >-
  Use when ...
tools: bash, read
model: claude-sonnet-4-6
---

System prompt 从这里开始...
```

## 身份审问（设计前必答）

```
1. 这个 Agent 的角色名是什么？（能用一个职业/职能描述吗？）
2. 它需要做哪些"无法脚本化"的判断？（至少列举一个）
3. 任务结束后，谁对结果负责？是 Agent 还是用户？
4. 如果换一个人扮演这个角色，他们需要什么专业背景？
```

回答不了第 1 或第 2 题 → 这是 Skill 需求，不是 Agent 需求。

## 详细文档

| 场景 | 文档 |
|------|------|
| 了解 Pi 框架能力、命令参数、生态 | [pi-coding-agents.md](pi-coding-agents.md) |
| Agent 身份框架、质量评分表 | [../02_framework/architecture.md](../02_framework/architecture.md) |
