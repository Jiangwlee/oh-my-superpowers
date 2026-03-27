# Insight Schema

## 核心字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | SHA256[:12]，基于 trigger + wrong_default 生成 |
| `trigger` | string | 是 | 什么情况下触发了错误行为 |
| `wrong_default` | string | 是 | 助手的错误默认行为 |
| `corrected_behavior` | string | 是 | 用户纠正后的正确行为 |
| `examples` | array | 否 | 纠正实例（session_id, before, after, context） |
| `tags` | array | 否 | 自由标签（从数据中涌现，非预设枚举） |
| `correction_count` | int | 是 | 纠正次数（≥2 才是高置信） |
| `confidence` | float | 是 | 0.0-1.0，带时间衰减 |
| `first_seen` | datetime | 是 | 首次观察时间 |
| `last_confirmed` | datetime | 是 | 最近一次确认时间 |
| `scope` | enum | 是 | `project`（仅限此项目）或 `user`（通用） |
| `why` | string | 否 | 为什么原来的做法是错的 |
| `source_session_ids` | array | 是 | 来源 session ID 列表 |
| `reframes` | array | 否 | 被此 insight 重新解读的 memory ID |

## 存储格式

Insight 存为 YAML frontmatter + markdown 文件：

```markdown
---
id: 3fae1e67394c
trigger: "使用 find 命令搜索文件"
wrong_default: "直接用 Bash 工具运行 find 命令"
corrected_behavior: "使用 Glob 工具搜索文件"
tags: ["tool-usage", "search"]
correction_count: 3
confidence: 0.8
first_seen: 2026-03-20T10:00:00
last_confirmed: 2026-03-27T15:00:00
scope: project
source_session_ids: ["sess-001", "sess-003"]
---

# 使用 find 命令搜索文件

## Wrong Default
直接用 Bash 工具运行 find 命令

## Corrected Behavior
使用 Glob 工具搜索文件

## Why
Glob 工具提供更好的用户体验，结果可审查

## Examples
### Example 1 (session: sess-001)
**Before:** Bash: find . -name "*.py"
**After:** Glob: pattern="**/*.py"
**Context:** 用户要求搜索 Python 文件
```

## 置信度规则

- 首次提取：0.3（dry-run）或 0.5（LLM 验证）
- 每次再确认：+0.1（上限 0.95）
- 时间衰减：待实现
- correction_count ≥ 2 才视为可靠 insight
