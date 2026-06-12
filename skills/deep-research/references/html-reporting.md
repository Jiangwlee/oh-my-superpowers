# HTML Reporting

Use the HTML page as a local publishing surface for a completed
`deep-research` workspace. Keep `brief.md`, `full-report.md`, and `state.json`
as the canonical audit artifacts.

## Inputs

Populate `assets/report-page-template.html` from these workspace files:

| Input | Fields Used |
|---|---|
| `reports/brief.md` | title, core conclusions, risks |
| `reports/full-report.md` | research goal, unresolved questions, per-source evidence value |
| `state.json` | topic, status, completed time, source count, source titles, platforms, URLs |

Page order is fixed: research goal, conclusions, risks, unresolved
questions, sources. Subquestion breakdown, research log, and the
facts/opinions/inferences layer stay in `full-report.md` only.

Do not paste webpage full text into the HTML page. Link sources and summarize
why each source matters.

## Generation

Create one generated page per reported workspace:

```text
reports/report.html
```

Replace template markers with escaped HTML. Convert Markdown lists and report
sections into semantic HTML:

| Marker | Expected HTML |
|---|---|
| `{{RESEARCH_GOAL}}` | paragraph or list from `full-report.md` |
| `{{CONCLUSION_CARDS}}` | `.conclusion-card` blocks from `brief.md` core conclusions: `<strong>` compact title (one clause, no trailing punctuation) + `<p>` one-to-three sentence summary with source link |
| `{{RISK_ITEMS}}` | `<li>` items from `brief.md` risks |
| `{{UNRESOLVED_ITEMS}}` | `<li>` items from `full-report.md` |
| `{{SOURCE_TABLE_ROWS}}` | `<tr>` rows: linked title, platform, one-line evidence value |

Write the conclusion-card title yourself: distill each core conclusion into
a short noun-or-verdict phrase. Do not repeat the summary text as the title.

If a section is empty, render a short neutral placeholder such as
`<p>Not reported.</p>`. Do not invent missing conclusions or sources.

## html-serve Publishing

Publish the generated file only when `HTML_SERVE_DATA_DIR` is configured.
Use this relative path convention:

```text
oh-my-superpowers/deep-research/<workspace-name>/report.html
```

Copy `reports/report.html` to:

```text
$HTML_SERVE_DATA_DIR/oh-my-superpowers/deep-research/<workspace-name>/report.html
```

Derive the review URL from:

```text
${HTML_SERVE_BASE_URL:-http://localhost:8888}/oh-my-superpowers/deep-research/<workspace-name>/report.html
```

Do not hardcode personal filesystem paths, LAN IPs, or Tailscale IPs in skill
files.

## Fallback

If html-serve is not configured or not running, still generate
`reports/report.html` inside the workspace and report that local path. The core
research output remains valid as long as `brief.md`, `full-report.md`, and
`state.json` exist.

## Audit Boundary

The HTML page is a readable projection of the workspace. It is not the audit
source. Use the workspace files for verification:

| Artifact | Audit Role |
|---|---|
| `plan.md` | subquestion scope and synthesis checkpoints |
| `reports/brief.md` | concise conclusion layer |
| `reports/full-report.md` | process log and full reasoning |
| `state.json` | status, report paths, and source metadata |

## Checklist

- The first viewport shows the topic, research goal, and the first
  conclusion cards.
- Each conclusion card has a distinct compact title, not a truncated copy
  of its summary.
- The source table includes URLs and evidence value.
- `reports/report.html` exists even when html-serve is unavailable.
- Published URLs are derived from `HTML_SERVE_BASE_URL`.
