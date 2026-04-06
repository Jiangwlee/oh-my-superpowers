# Workspace

默认根目录：`~/.local/share/oh-my-superpowers/deep-research/`

每次研究创建一个独立 workspace：

```text
YYYY-MM-DDTHH-mm-<slug>/
├── plan.md          ← Phase 0 结束后立即创建，每轮更新 checkbox
├── reports/
│   ├── brief.md
│   └── full-report.md
└── state.json
```

- `plan.md` 保存研究计划（3-6 条，带 checkbox），是每轮 Synthesis Check 的基准
- `reports/` 保存最终输出（brief + full report）
- `state.json` 保存研究元数据和 sources 列表
