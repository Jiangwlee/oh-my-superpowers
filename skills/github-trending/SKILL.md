---
name: github-trending
description: >-
  Generate a daily GitHub trending project-intelligence report: fetch trending
  repos, study README/API evidence, answer each repo's purpose/content/value in
  Chinese, and publish a lens-first HTML digest to html-serve. Use when the user
  asks for GitHub trending, hot repos, 今日 GitHub 热门, trending 项目报告, or a
  daily open-source project digest. Do NOT use for deep research on a single
  repo (use deep-research) or general AI news briefs (use daily-ai-brief).
---

# GitHub Trending

Pipeline: Fetch → Study → Analyze → Render → Publish

## Output Contract

This skill exists to answer one daily question: **今天的热门项目到底在解决什么问题、做了什么、创造了什么价值？**

For every repo, produce a Chinese three-lens analysis:

| Lens | Required answer | Evidence to use |
|---|---|---|
| **项目目的** | It solves what problem, for whom, in what context. | README intro, tagline, topics, homepage, repo description. |
| **项目内容** | It actually provides what product, library, workflow, model, app, or infrastructure. | README features, install/usage, directory/docs when cloned. |
| **项目价值** | It creates what practical value: speed, cost, quality, access, automation, developer leverage, or ecosystem signal. | Use cases, adoption signals, stars-today, comparisons, integration surface. |

Do not treat stars as value by themselves. Stars are attention; value must be stated as a user-facing or ecosystem-facing gain.

## Workflow

### Stage 1: Fetch

```bash
omp github-trending fetch --since daily --out /tmp/trending.json
```

Options: `--since daily|weekly|monthly`, `--lang <language>`, `--readme-chars N`.
Output: JSON array, one object per repo with `name`, `desc`, `lang`,
`stars_today`, `stars`, `forks`, `topics`, `license`, `created_at`, `readme`.
Repos that failed enrichment carry an `error` field instead.

Done when: JSON file exists with 10+ repos, or the hard gate explains why it cannot.

### Stage 2: Study

Read the JSON before writing. Use `readme`, `full_desc`, `topics`, `homepage`, language, age, and stars-today to infer the three lenses.

Only clone when the three lenses are still unclear and the repo ranks in the top 4:

```bash
git clone --depth 1 https://github.com/<owner>/<repo> /tmp/<repo>
```

Inspect README, docs, examples, package metadata, and top-level structure. Never clone more than 3 repos.

Done when: every repo has evidence for purpose/content/value, or an explicit uncertainty note.

### Stage 3: Analyze

For each repo, write these fields in Chinese:

| Field | Length | Rule |
|---|---:|---|
| `purpose` | 1 sentence | Name the pain point or job-to-be-done. |
| `content` | 1 sentence | Say what the repo contains or enables, not only what category it belongs to. |
| `value` | 1 sentence | State the practical gain or strategic signal. |
| `trend_reason` | 0-1 sentence | Explain why it may be trending today when evidence supports it. |
| `summary` | 1 sentence | A compact editorial judgment tying the three lenses together. |

Then write `今日看点`: one paragraph that names the day's dominant problem cluster, the strongest value signal, and the top mover.

Done when: every repo answers all three lenses; uncertain claims are marked as uncertain instead of invented.

### Stage 4: Render

Choose one template from `assets/` based on the report's reading goal. If the user names a template, use it. Otherwise choose freely.

| Template | Use when | Required fragments |
|---|---|---|
| `report-template.html` | The report should read like an editorial digest with a strong lead story. | `{{FOCUS_REPOS}}`, `{{REST_REPOS}}` |
| `signal-dashboard-template.html` | The report should emphasize trend clusters, signal strength, and fast scanning. | `{{TREND_MAP}}`, `{{REPO_SIGNAL_CARDS}}` |

Sort repos by stars-today descending. Keep the same analysis obligation regardless of template:

| Rank | Required emphasis |
|---:|---|
| 1 | purpose/content/value + editorial judgment. |
| 2-4 | compact three-lens analysis. |
| 5+ | scannable three-lens rows or cards. |

Replace all `{{MARKER}}` placeholders. Generate escaped HTML fragments using the structure documented in the chosen template comments. HTML-escape repo descriptions, README-derived text, topics, and analysis.

Write the rendered HTML to a temporary local file. Filename convention:
`<YYYY-MM-DD>.html` (weekly/monthly runs: `<YYYY-MM-DD>-<since>.html`).

Also write the analyzed data to a sibling `<same-name>.json` so later agents can
query the report structurally instead of parsing HTML:

```json
{
  "date": "<YYYY-MM-DD>",
  "since": "daily",
  "highlight": "<今日看点 paragraph>",
  "repos": [
    {
      "name": "owner/repo", "url": "https://github.com/owner/repo",
      "lang": "...", "stars_today": 0, "stars": 0, "topics": ["..."],
      "desc": "...", "purpose": "...", "content": "...", "value": "...",
      "trend_reason": "...", "summary": "..."
    }
  ]
}
```

Keep `repos` in the same stars-today order as the HTML.

Done when: local HTML and JSON files exist, no `{{` markers remain in the HTML, and every repo in the JSON carries purpose/content/value.

### Stage 5: Publish

Publish through html-serve CLI:

```bash
omp html-serve publish <tmp.html> --to github-trending/<filename>.html --source github-trending --tag github --tag trending
omp html-serve publish <tmp.json> --to github-trending/<filename>.json --source github-trending --tag github --tag trending --tag data --title "GitHub Trending <YYYY-MM-DD> data"
```

Tell the user both returned URLs of the HTML: `localhost_url` and `tailscale_url`.

Done when: both `omp html-serve publish` calls succeed and the HTML URLs are given to user.

## Hard Gate

| Condition | Action |
|---|---|
| `fetch` returns no repos | Abort; tell user to check network or report page-structure breakage. |
| `gh` not authenticated | Continue; the script falls back to anonymous API with 60 req/h. Suggest `gh auth login` for higher limits. |
| More than half of repos carry `error` | Warn user about API rate limit; suggest `gh auth login` or retry later. |
| A repo's purpose/content/value cannot be inferred | Mark the specific lens as `证据不足`; do not hallucinate. Clone only if it is top 4 and clone budget remains. |
| `omp html-serve publish` reports missing `HTML_SERVE_DATA_DIR` | Ask user to configure `docker/html-serve/.env` or export it; do not write to a hardcoded path. |
| html-serve container not running | Tell user: `omp html-serve start`. |
| Template file missing | Abort; tell user to reinstall the skill. |

## Command Hierarchy

```text
omp
└── github-trending
    └── fetch --since daily|weekly|monthly --lang <language> --readme-chars N --out <path>
```
