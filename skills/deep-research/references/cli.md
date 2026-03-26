# CLI Reference

统一入口：

```bash
omp-deep-research <subcommand> [args]
```

## `init`

创建新的 research workspace。

```bash
omp-deep-research init --topic "<topic>" [--slug "<slug>"] [--mode quick|default|deep]
```

输出：JSON，包含：
- `workspace`
- `state_file`
- `round_log_file`
- `reports_dir`

## `save-source`

保存一篇来源的原始网页内容和元信息。

```bash
omp-deep-research save-source --workspace "<workspace>" --url "<url>" --title "<title>" --platform "<platform>" --content-file "<file>"
```

也支持：

```bash
omp-deep-research save-source --workspace "<workspace>" --url "<url>" --title "<title>" --platform "<platform>" --content "<text>"
```

输出：JSON，包含：
- `source_id`
- `raw_file`
- `meta_file`
- `note_file`

## `update-state`

合并 round log、source note、hypotheses、next step 等结构化研究状态。

```bash
omp-deep-research update-state --workspace "<workspace>" --payload-file "<json_file>"
```

详见 [`state-schema.md`](state-schema.md)。

## `build-report`

写入 `brief` 和 `full report` 到 workspace 的 `reports/` 目录。

```bash
omp-deep-research build-report --workspace "<workspace>" --brief-file "<brief_md>" --full-report-file "<full_report_md>"
```

也支持：

```bash
omp-deep-research build-report --workspace "<workspace>" --brief "<markdown>" --full-report "<markdown>"
```
