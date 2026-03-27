---
name: insight
description: >-
  项目记忆系统。回忆/回顾经验教训(recall)，提取/记住对话经验(capture)，
  提炼洞察模式(evaluate)，查看记录(list)。
---

# Insight Skill

## 直接执行（不需要推理，直接跑命令）

| 用户意图 | 命令 |
|---------|------|
| 回忆/想起/回顾 经验、教训、踩坑 | `omp-insight recall --source . --format md --budget 4096` |
| 提取/记住/保存 当前对话经验 | `omp-insight capture --source .` |
| 提炼/归纳/总结 洞察模式 | `omp-insight evaluate --source .` |
| 查看/列出 记忆或洞察 | `omp-insight list --source .` |
| 提升 memory 为 insight | `omp-insight promote <id> --reason "<text>"` |
| 降级 insight | `omp-insight degrade <id> --reason "<text>"` |
| 删除记录 | `omp-insight delete <id>` |

> **规则**：收到用户意图后直接执行对应命令，不需要先搜索文件、检查命令是否存在、或阅读其他文档。

## 完整参数

```bash
omp-insight capture  --source <dir> [--session <id>] [--since 7d] [--min-messages 10] [--force] [--dry-run] [--model sonnet]
omp-insight recall   --source <dir> [--format json|md] [--budget 4096] [--dry-run]
omp-insight evaluate --source <dir> [--dry-run] [--prompt-file <path>]
omp-insight list     --source <dir> [--type memory|insight]
omp-insight promote  <id> [--reason <text>] [--source <dir>]
omp-insight degrade  <id> [--reason <text>] [--source <dir>]
omp-insight delete   <id> [--source <dir>]
```

## 参考文档（按需加载）

需要深入理解内部机制时，加载对应文档：

- **数据结构**：`references/insight-schema.md` — memory/insight 的字段定义和 YAML 格式
- **提取流程**：`references/extraction-flow.md` — capture/evaluate 的完整处理流程
- **消费协议**：`references/consumption-protocol.md` — 其他 Agent 集成 insight 的协议
- **文档索引**：`references/README.md` — 所有参考文档的入口
