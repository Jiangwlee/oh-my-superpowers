---
name: github-trending
description: >-
  Generate a GitHub trending report: fetch today's trending repos, enrich each
  with GitHub API details and README excerpts, write Chinese editorial
  commentary, and publish an HTML digest to html-serve. Use when the user asks
  for GitHub trending, hot repos, "今日 GitHub 热门", "trending 项目报告", or a
  daily open-source digest. Do NOT use for deep research on a single repo (use
  deep-research) or general AI news briefs (use daily-ai-brief).
---

# GitHub Trending

Pipeline: Fetch → Study → Comment → Render → Publish

## Workflow

### Stage 1: Fetch

```bash
omp github-trending fetch --since daily --out /tmp/trending.json
```

Options: `--since daily|weekly|monthly`, `--lang <language>`, `--readme-chars N`.
Output: JSON array, one object per repo with `name`, `desc`, `lang`,
`stars_today`, `stars`, `forks`, `topics`, `license`, `created_at`, `readme`.
Repos that failed enrichment carry an `error` field instead.

Done when: JSON file exists with 10+ repos.

### Stage 2: Study

Read the JSON. For each repo, the `readme` excerpt plus API metadata is
usually enough. Only when a repo is still unclear and it ranks in the top 4:

```bash
git clone --depth 1 https://github.com/<owner>/<repo> /tmp/<repo>
```

Inspect its docs/structure, then continue. Never clone more than 3 repos.

Done when: every repo can be summarized in 1-3 sentences.

### Stage 3: Comment

Write for each repo a Chinese commentary (1-3 sentences): what it is, why it
trends today, and relevance to the user's work when obvious. Then write one
`今日看点` paragraph naming the day's dominant theme and the top mover.

Done when: every repo has commentary; takeaway written.

### Stage 4: Render

Load `assets/report-template.html`. Sort repos by stars-today descending:
rank 1 fills the Lead block, ranks 2-4 fill 焦点项目, the rest fill 完整榜单.
Replace all `{{MARKER}}` placeholders (structure comments are in the template).
HTML-escape repo descriptions and commentary.

Write to: `$HTML_SERVE_DATA_DIR/github-trending/<YYYY-MM-DD>.html`
(weekly/monthly runs: `<YYYY-MM-DD>-<since>.html`).

Done when: HTML file written, no `{{` markers remain.

### Stage 5: Publish

Tell the user the URL:
`${HTML_SERVE_BASE_URL:-http://localhost:${HTML_SERVE_PORT:-8888}}/github-trending/<filename>.html`.
Prefer `HTML_SERVE_BASE_URL` when set. Verify with a HEAD request returning 200.

Done when: URL verified and given to user.

## Hard Gate

| Condition | Action |
|---|---|
| `fetch` returns no repos | Abort; tell user to check network or report page-structure breakage |
| `gh` not authenticated | Continue (script auto-falls back to anonymous API, 60 req/h); suggest `gh auth login` for higher limits |
| More than half of repos carry `error` | Warn user about API rate limit; suggest `gh auth login` or retry later |
| `HTML_SERVE_DATA_DIR` unset | Ask user to configure `docker/html-serve/.env` or export it; do not write to a hardcoded path |
| html-serve container not running | Tell user: `cd docker/html-serve && docker compose up -d` |
| Template file missing | Abort, tell user to reinstall skill |
