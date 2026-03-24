# Agent Design: <name>

## 身份
- 角色：<职业描述>
- 专业领域：<边界描述>
- 判断点：<无法脚本化的判断，至少一条>
- 签名输出：<Agent 对什么结果负责>

## Skill 依赖
- <skill-name>：<用途>
- 缺口（需先开发）：<skill-name> — <用途>

## 推理循环
- 类型：线性 / 迭代
- 最少迭代：N 轮（仅迭代型）
- 停止条件：<描述>

## 输出模板
<结构草稿，用占位符>

## Pi Frontmatter 草稿
```yaml
---
name:
description: >-
  Use when ...
  Do NOT use when ...
tools:
model: claude-sonnet-4-6
---
```

## Trigger Eval
- 应触发：<场景>
- 不应触发：<场景>
