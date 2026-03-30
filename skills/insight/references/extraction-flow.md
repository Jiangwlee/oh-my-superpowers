# Insight 提取流程（v3 三层 Pipeline）

## 流程总览

```
[手动触发: omp-insight capture / evaluate]
        │
        ▼
┌─ Session Discovery ───────────────────────────┐
│  扫描 ~/.claude/projects/ (Claude Code)        │
│  扫描 ~/.codex/sessions/  (Codex)              │
│  扫描 ~/.pi/agent/sessions/ (Pi)               │
│  扫描 ~/.openclaw/ (OpenClaw)                  │
│  → 按项目路径匹配，按时间过滤                  │
└───────────────────────────────────────────────┘
        │
        ▼
┌─ Session Reader ──────────────────────────────┐
│  解析 JSONL → UnifiedMessage[] 统一格式        │
│  提取: role, content, timestamp, tool_calls    │
│  跳过: progress, file-history-snapshot, system │
└───────────────────────────────────────────────┘
        │
        ▼
┌─ Layer 1: Capture (LLM) ─────────────────────┐
│  角色：复盘分析师                              │
│  输入：session 对话                            │
│  输出：6 字段结构化 Memory（per-session）      │
│  字段：kind/scope/summary/source/evidence_ref  │
│         /confidence（+ 可选 tags）             │
│  增量处理：cursor-based，不重复已见 session    │
└───────────────────────────────────────────────┘
        │
        ▼
┌─ Layer 2: Aggregate (代码) ──────────────────┐
│  纯 Python 确定性聚合，不调用 LLM             │
│  输入：store.list_memories() 全量 Memory      │
│  处理：                                       │
│    - GROUP BY kind/scope → 频次统计           │
│    - 时间窗口趋势（recent_7d / recent_30d）   │
│    - 精确去重                                 │
│    - confidence 加权                          │
│    - tag 共现检测                             │
│  输出：AggregateResult JSON + 每组 top-5 样本 │
└───────────────────────────────────────────────┘
        │
        ▼
┌─ Layer 3: Evaluate (LLM) ────────────────────┐
│  角色：持续改进顾问                            │
│  输入：聚合统计 JSON + 代表性样本              │
│  输出：Insight[]（极少、高价值模式）           │
│  evidence 字段：支撑的 kind 列表              │
│  先单路，数据量 >1000 或质量下降时拆 facet    │
└───────────────────────────────────────────────┘
        │
        ▼
┌─ Store ───────────────────────────────────────┐
│  Memory/Insight 写入 markdown 文件             │
│  元数据管理：SQLite（evidence_links, hit_logs）│
│  recall 时按 decay score 排序召回              │
└───────────────────────────────────────────────┘
```

## Memory 6 字段 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | enum: bug/decision/pattern/friction/workflow/other | 最小可计算分类 |
| `scope` | enum: file/module/skill/agent/project/other | 影响范围 |
| `summary` | string (≤100字) | 人类可读短文本 |
| `source` | string | "session_id@runtime" |
| `evidence_ref` | string | 原始证据位置 |
| `confidence` | float 0.0-1.0 | 置信度 |

可选字段：`tags: list[str]`

## 运行模式

| 模式 | 命令 | LLM 调用 | 用途 |
|------|------|---------|------|
| Capture dry-run | `omp-insight capture --dry-run` | 有（提取但不写入） | 预览 memory 提取结果 |
| Capture | `omp-insight capture` | 有 | 正式提取 memory |
| Evaluate dry-run | `omp-insight evaluate --dry-run` | 无 | 查看聚合统计 |
| Evaluate | `omp-insight evaluate` | 有 | 从聚合结果提炼 insight |
