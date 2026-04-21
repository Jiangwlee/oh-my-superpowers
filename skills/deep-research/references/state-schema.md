# State Schema

`state.json` 在 `init` 时创建，`build-report` 时更新为终态。

## init 后

```json
{
  "topic": "Claude Code memory",
  "slug": "claude-code-memory",
  "mode": "default",
  "workspace": "/abs/path/to/workspace",
  "created_at": "2026-03-26T14:30:00",
  "status": "initialized",
  "report_files": {"brief": null, "full_report": null}
}
```

## build-report 后

```json
{
  "topic": "Claude Code memory",
  "slug": "claude-code-memory",
  "mode": "default",
  "workspace": "/abs/path/to/workspace",
  "created_at": "2026-03-26T14:30:00",
  "status": "reported",
  "completed_at": "2026-03-26T15:10:00",
  "sources": [
    {"url": "https://example.com/article", "title": "Example Article", "platform": "google"}
  ],
  "report_files": {
    "brief": "/abs/path/to/workspace/reports/brief.md",
    "full_report": "/abs/path/to/workspace/reports/full-report.md"
  }
}
```

## `sources` 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `url` | 是 | 来源 URL |
| `title` | 否 | 来源标题 |
| `platform` | 否 | 来源平台（google / github / reddit / x 等） |
