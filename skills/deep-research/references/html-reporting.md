# HTML Reporting

`build-report` renders `reports/report.html` from `assets/report-page-template.html`. The HTML page is a sharing surface; `plan.md`, `brief.md`, `full-report.md`, and `state.json` remain the audit source.

## Inputs

| Source | Used for |
|---|---|
| `reports/brief.md` | title, core conclusions, risks |
| `reports/full-report.md` | research goal, unresolved questions, source evidence summaries |
| `state.json` | topic, status, completed time, source count, source URLs |

The page order is fixed: goal → conclusions → risks → unresolved questions → sources. Keep subquestion details, research log, and fact/opinion/inference separation in `full-report.md` only.

Do not paste webpage full text into HTML. Link sources and summarize why each matters.

## Generation Contract

`omp deep-research build-report` must:

1. Read `assets/report-page-template.html`.
2. Write `reports/report.html`.
3. Record `state.json.report_files.html`.
4. Fail if any `{{MARKER}}` placeholder remains.

If input sections are missing, render neutral placeholders. Do not invent missing conclusions or sources.

## Publish

Publish only when html-serve is configured:

```bash
omp html-serve publish reports/report.html --to deep-research/<workspace-name>.html --source deep-research --tag research --tag <topic-tag>
```

Use the workspace directory name unless the user asks for a specific report name. Return both `localhost_url` and `tailscale_url`.

If publishing fails because html-serve is unavailable, still return the local `reports/report.html` path and explain that it was not published.

## Checklist

- `reports/report.html` exists.
- No `{{MARKER}}` placeholders remain.
- The source table includes source URLs and evidence value.
- Published path is `deep-research/<report-name>.html`, not an `oh-my-superpowers/` subdirectory.
