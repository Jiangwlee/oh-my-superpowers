# Workspace

默认根目录：`~/.local/share/oh-my-superpowers/deep-research/`。每次研究创建独立 workspace：

```text
YYYY-MM-DDTHH-mm-<slug>/
├── plan.md          ← Phase 0 末立刻创建，每轮更新 checkbox
├── reports/
│   ├── brief.md
│   └── full-report.md
└── state.json
```

| 文件 | 作用 |
|---|---|
| `plan.md` | 研究计划（3-6 条 checkbox），每轮 Synthesis Check 的基准 |
| `reports/` | 最终输出：brief + full report |
| `state.json` | 元数据 + sources 列表（schema 见 `state-schema.md`） |
