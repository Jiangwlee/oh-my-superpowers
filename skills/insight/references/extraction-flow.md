# Insight 提取流程

## 流程总览

```
[手动触发: omp-insight extract]
        │
        ▼
┌─ Session Discovery ───────────────────────────┐
│  扫描 ~/.claude/projects/ (Claude Code)        │
│  扫描 ~/.codex/sessions/  (Codex)              │
│  扫描 ~/.pi/agent/sessions/ (Pi)               │
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
┌─ Correction Detection（启发式预过滤）──────────┐
│  滑动窗口扫描用户消息                          │
│  匹配纠正关键词: 不对/错了/应该是/wrong/no...  │
│  提取上下文窗口: 纠正前助手行为 + 纠正后行为   │
│  输出: CorrectionTrajectory[]                  │
│  合并同 session 相邻纠正                       │
└───────────────────────────────────────────────┘
        │
        ▼ (dry-run 到此为止)
┌─ LLM 精筛 ────────────────────────────────────┐
│  将候选片段送给 LLM（claude -p）               │
│  判断: is_valid? 是否真正有价值的 delta         │
│  提炼: trigger / wrong_default / corrected     │
│  标注: tags, scope, confidence, why            │
│  输出: Insight[]                               │
└───────────────────────────────────────────────┘
        │
        ▼
┌─ Store ───────────────────────────────────────┐
│  写入 markdown 文件（QMD 可索引）              │
│  更新 SQLite 索引 + FTS5                       │
│  存储 evidence links                           │
│  如 QMD 可用，更新 QMD collection              │
└───────────────────────────────────────────────┘
```

## 双路数据管道

| 路径 | 信号源 | 信噪比 | 优先级 |
|------|--------|--------|--------|
| 显式纠正 | 用户说"不对"/"错了"/"应该是" | 高 | 优先处理 |
| 隐式纠正 | 反复尝试/路径偏离/回退重来 | 中 | 延迟处理（v0.2） |

当前 v0.1 仅实现显式纠正路径。

## 运行模式

| 模式 | 命令 | LLM 调用 | 用途 |
|------|------|---------|------|
| Dry-run | `--dry-run` | 无 | 快速查看纠正模式数量和分布 |
| 正式提取 | 默认 | 每个候选一次 | 高质量 insight 提取 |
