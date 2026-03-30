# Insight Schema（v3）

## Memory Schema（6 字段）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | `mem_{hex_timestamp}_{random8}` |
| `kind` | enum | 是 | bug / decision / pattern / friction / workflow / other |
| `summary` | string | 是 | 人类可读短文本（≤100字） |
| `scope` | enum | 是 | file / module / skill / agent / project / other |
| `source` | string | 是 | `session_id@runtime`（来源定位） |
| `evidence_ref` | string | 是 | 原始证据位置（消息序号、文件路径等） |
| `created_at` | datetime | 是 | 创建时间 |
| `hit_count` | int | 是 | recall 命中次数（默认 0） |
| `confidence` | float | 是 | 0.0-1.0（默认 0.5） |
| `tags` | array | 否 | 自由标签列表 |

### kind 枚举

| 值 | 说明 |
|----|------|
| `bug` | 发现的缺陷或错误 |
| `decision` | 技术/产品决策 |
| `pattern` | 反复出现的行为模式 |
| `friction` | 摩擦点、低效环节 |
| `workflow` | 工作流程/协作方式 |
| `other` | 无法归入上述类别 |

枚举允许 `other`，枚举表是产品资产，`other` 积累后人工决策是否扩展。

### scope 枚举

| 值 | 说明 |
|----|------|
| `file` | 单个文件 |
| `module` | 模块级 |
| `skill` | 技能级 |
| `agent` | Agent 级 |
| `project` | 项目级 |
| `other` | 无法归入上述类别 |

## Insight Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | `ins_{hex_timestamp}_{random8}` |
| `pattern` | string | 是 | 一句话描述模式 |
| `action` | string | 是 | Agent 应该怎么做 |
| `evidence` | array | 是 | 支撑此 insight 的 kind 列表 |
| `scope` | enum | 是 | 影响范围 |
| `created_at` | datetime | 是 | 创建时间 |
| `last_validated_at` | datetime | 是 | 最近验证时间 |
| `evidence_count` | int | 是 | 证据数量 |
| `confidence` | float | 是 | 0.0-1.0（默认 0.6） |
| `tags` | array | 否 | 标签列表 |

## 存储格式

Memory 和 Insight 均存为 YAML frontmatter markdown 文件：

```markdown
---
id: mem_19527a3f1b_c8e4a2d1
kind: friction
summary: "Claude 未验证修复就报告完成，导致多轮调试"
scope: project
source: "sess-001@claude"
evidence_ref: "message #42-45"
created_at: "2026-03-30T10:00:00"
hit_count: 0
confidence: 0.85
tags: ["debugging", "verification"]
---
```

## 置信度规则

- Capture 时由 LLM 判定初始 confidence（0.0-1.0）
- recall 命中时 hit_count 递增
- 排序使用 decay score：`hit_count * confidence - age_penalty`
- 宽限期 3 个月内无衰减，之后每月 -0.5
