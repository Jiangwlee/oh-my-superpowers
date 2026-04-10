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

输出：JSON，包含：
- `workspace`
- `state_file`
- `reports_dir`

## `build-report`

写入 `brief` 和 `full report` 到 workspace 的 `reports/` 目录，同时将 sources 列表持久化到 `state.json`。

```bash
omp deep-research build-report --workspace "<workspace>" --brief-file "<brief_md>" --full-report-file "<full_report_md>" [--sources-file "<sources_json>"]
```

也支持 inline 形式：

```bash
omp deep-research build-report --workspace "<workspace>" --brief "<markdown>" --full-report "<markdown>" [--sources-file "<sources_json>"]
```

### `--sources-file` 格式

JSON 文件，内容为 sources 数组：

```json
[
  {"url": "https://example.com/article", "title": "Example Article", "platform": "google"},
  {"url": "https://github.com/owner/repo", "title": "Repo Name", "platform": "github"}
]
```

- `url` 必填，`title` 和 `platform` 可选
- 未提供 `--sources-file` 或数组为空时，打印 warning 但不阻断
