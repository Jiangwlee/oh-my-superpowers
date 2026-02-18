# Skill 可复用模板

## 标准模板（可直接复制）

```markdown
---
name: <skill-name>
description: Use when <用户意图/触发句式/适用边界>.
---

# <Skill Title>

## Overview
- 目标：
- 输入：
- 输出：

## When to Use
- 触发信号 1：
- 触发信号 2：
- 不适用场景：

## Workflow
1. 收集必要输入（缺失则先询问）
2. 选择路径（给出分支条件）
3. 执行核心步骤（命令/工具）
4. 校验结果并返回

## Guardrails
- 安全约束：
- 失败重试策略：

## References
- 需要时读取：`references/<topic>.md`

## Scripts
- 优先调用：`scripts/<tool>.sh --help`
```

## description 写法参考

| 场景 | description 示例 |
|------|-----------------|
| 调试类 | `Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes` |
| 实现类 | `Use when implementing any feature or bugfix, before writing implementation code` |
| 规划类 | `Use when you have a spec or requirements for a multi-step task, before touching code` |
| 验证类 | `Use when about to claim work is complete, fixed, or passing, before committing or creating PRs` |
| 会话启动类 | `Use when starting any conversation - establishes [X]` |
