---
name: insight
description: >-
  Use when you need to extract behavioral insights from AI conversation history
  (Claude Code, Codex, Pi), or when you need to retrieve past insights to avoid
  repeating mistakes. Extracts correction patterns where the user repeatedly
  corrected the AI until reaching the right approach, and stores them as
  structured, searchable behavioral deltas.
  Do NOT use for general knowledge management, note-taking, or documentation.
  Do NOT use for real-time conversation monitoring (manual trigger only).
---

# Insight Skill

从 AI 对话中提取高质量经验洞察（behavioral delta），替代 ECC instinct 系统。

## 核心概念

**Behavioral Delta**：行为差分——在特定 trigger 下，错误默认行为 → 正确纠正行为的 diff。
这是系统的原子价值单元，不是规则，不是故事。

## 三层架构

```
Session（原始对话）→ Memory（结构化行为记录）→ Insight（跨会话高价值经验）
```

## CLI 命令

### 提取 insight

```bash
# 从当前项目的所有 runtime 会话中提取（推荐先 dry-run）
omp-insight extract --dry-run

# 指定 runtime 和时间范围
omp-insight extract --runtime claude --since 2026-03-20

# 正式提取（调用 LLM 精筛）
omp-insight extract --model sonnet
```

### 检索 insight

```bash
# 搜索相关 insight（项目级 + 用户级）
omp-insight search "文件搜索应该用什么工具"

# 仅搜索项目级
omp-insight search "代码风格" --scope project

# JSON 格式输出（给其他工具消费）
omp-insight search "error handling" --json --top-k 3
```

### 管理 insight

```bash
# 列出所有 insight
omp-insight list --sort confidence

# 查看详情
omp-insight show <insight-id>

# 提升到 user 级（跨项目通用）
omp-insight promote <insight-id>

# 查看统计
omp-insight stats
```

## Agent 消费协议

Agent 在执行新任务前，**必须**：

1. 调用 `omp-insight search "<当前任务关键词>"` 检索 top-5 相关 insight
2. 声明："根据历史经验，我将避免以下错误：..."
3. 任务完成后，调用 `omp-insight` 记录消费结果

详见 `references/consumption-protocol.md`。

## 存储

- **Insight 文件**：YAML frontmatter + markdown，存于 `~/.local/share/oh-my-superpowers/insight/`
- **检索引擎**：QMD 混合检索（BM25 + 向量）；QMD 不可用时降级为 SQLite FTS5
- **元数据**：SQLite（evidence_links, consumption_logs）

## 参考文档

- `references/README.md` — 文档索引
- `references/insight-schema.md` — Insight schema 详解
- `references/extraction-flow.md` — 提取流程详解
- `references/consumption-protocol.md` — Agent 消费协议
