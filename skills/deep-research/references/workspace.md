# Workspace

默认根目录：`~/.local/share/oh-my-superpowers/deep-research/`

每次研究创建一个独立 workspace：

```text
YYYY-MM-DDTHH-mm-<slug>/
├── raw/
│   ├── S001.txt
│   └── S001.meta.json
├── notes/
│   └── S001.md
├── reports/
│   ├── brief.md
│   └── full-report.md
├── state.json
└── rounds.jsonl
```

约束：
- `raw/` 保存原始网页内容和元信息
- `notes/` 保存 source-level note
- `reports/` 保存最终输出
- `state.json` 是当前压缩研究状态
- `rounds.jsonl` 是逐轮审计日志
