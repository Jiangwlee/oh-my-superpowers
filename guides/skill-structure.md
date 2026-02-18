# Skill 结构与命名规范

## 目录约定

- 开发中的 skills 放在：`skills/`
- 外部优秀仓库缓存放在：`github_cache/`
- 开发经验文档放在：`guides/`

## 单个 Skill 推荐目录结构

```text
skills/<skill-name>/
  SKILL.md                # 必需
  scripts/                # 可选：可执行脚本
  references/             # 可选：按需加载文档
  assets/                 # 可选：模板/资源文件
```

## 命名规范

- `name` 使用小写 + 连字符：`my-skill-name`
- 目录名与 `name` 保持一致
- 优先"动作 + 领域"的表达方式，避免过长或含义模糊

## SKILL.md 最小规范

```markdown
---
name: my-skill-name
description: Use when [触发条件 + 场景 + 边界]
---

# My Skill

## Overview
[一句话说明做什么]

## Workflow
[关键步骤，必要时给决策分支]

## Examples
- [用户表达 -> 你应该执行什么]
```

关键点：

- `name`、`description` 是触发与发现的核心元数据
- `description` 重点写"何时使用（Use when...）"，而不是"怎么实现"
- 正文写可执行步骤，少写泛泛方法论
