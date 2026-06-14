# Workspace

Default root: `~/.local/share/oh-my-superpowers/deep-research/`.
Override with `DEEP_RESEARCH_DATA_DIR`.

Each run creates one workspace:

```text
YYYY-MM-DDTHH-mm-<slug>/
├── plan.md
├── reports/
│   ├── brief.md
│   ├── full-report.md
│   └── report.html
└── state.json
```

| Path | Role |
|---|---|
| `plan.md` | 3-6 subquestions; update checkbox status after each synthesis. |
| `reports/brief.md` | Concise conclusion layer. |
| `reports/full-report.md` | Full process log, source reasoning, and evidence separation. |
| `reports/report.html` | Readable projection for sharing; not the audit source. |
| `state.json` | Topic, mode, source list, timestamps, and report paths. |

## `state.json`

Created by `init`, completed by `build-report`.

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
    {
      "url": "https://example.com/article",
      "title": "Example Article",
      "platform": "google",
      "summary": "Why this source matters."
    }
  ],
  "report_files": {
    "brief": "/abs/path/to/workspace/reports/brief.md",
    "full_report": "/abs/path/to/workspace/reports/full-report.md",
    "html": "/abs/path/to/workspace/reports/report.html"
  }
}
```

`source.url` is required. `title`, `platform`, `summary`, `evidence`, and `evidence_value` are optional; summary/evidence fields feed the HTML source table.
