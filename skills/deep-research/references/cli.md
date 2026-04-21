# CLI Reference

统一入口：

```bash
omp deep-research <subcommand> [args]
```

## `init`

创建新的 research workspace。

```bash
omp deep-research init --topic "<topic>" [--slug "<slug>"] [--mode quick|default|deep]
```

输出 JSON，包含 `workspace`、`state_file`、`reports_dir`。

## `build-report`

写入 `brief` + `full report` 到 workspace 的 `reports/`，并把 sources 列表持久化到 `state.json`。

文件形式：

```bash
omp deep-research build-report --workspace "<workspace>" \
  --brief-file "<brief_md>" --full-report-file "<full_report_md>" \
  [--sources-file "<sources_json>"]
```

内联形式：

```bash
omp deep-research build-report --workspace "<workspace>" \
  --brief "<markdown>" --full-report "<markdown>" \
  [--sources-file "<sources_json>"]
```

### `--sources-file` 格式

JSON 数组：

```json
[
  {"url": "https://example.com/article", "title": "Example Article", "platform": "google"},
  {"url": "https://github.com/owner/repo", "title": "Repo Name", "platform": "github"}
]
```

- `url` 必填；`title`、`platform` 可选
- 未提供或数组为空：打印 warning，不阻断
