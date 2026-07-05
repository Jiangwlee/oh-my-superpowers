---
name: daily-ai-brief
description: >-
  Generate a daily AI tech brief: scan configured sources (X accounts, blogs,
  tech communities), filter high-value items, and render a card-based HTML
  newsletter. Use when the user asks for a daily AI digest, tech briefing,
  information scan, or says "今日简报", "AI 日报", "tech brief", "扫一遍今天的信息".
  Do NOT use for deep research on a single topic (use deep-research),
  or for X account content curation without the brief format.
---

# Daily AI Brief

Pipeline: Sources → Scan → Filter → Render

## Workflow

### Stage 1: Sources

Load `references/sources.yaml`. Use defaults unless user overrides.

Done when: source list confirmed.

### Stage 2: Scan

Collect past-24h candidates from each source. All X searches run **serially**.

| Source type | Command | Notes |
|---|---|---|
| X accounts | `omp web-operator search x "from:<handle> since:YYYY-MM-DD" 10` | `since` = yesterday; no keyword filter |
| X for-you | `omp web-operator x for-you` | Supplementary signal |
| Blogs/sites | `omp web-operator read-url <url>` | |

Collect per candidate: url, source_name, source_type, raw_text, timestamp.
Target: 15-30 raw candidates.

| Situation | Action |
|---|---|
| No result (person didn't post in 24h) | Skip silently, do not mention in footer |
| Error/timeout (network, command failure) | Skip, note in output footer |

Done when: candidates collected, each with url and raw text.

### Stage 3: Filter

Load `references/editorial-criteria.md`.

1. Deduplicate — same story from multiple sources → keep primary
2. Score against editorial criteria, select 10-15 items
3. Write editorial verdict ("对你意味着什么") for each selected item

Assign tier:

| Tier | Count | Criteria |
|---|---|---|
| **L1 Headline** | 1-2 | Changes immediate decisions; first to report |
| **L2 Picks** | 5-10 | Practical value; worth knowing |
| **L3 Radar** | 2-5 | Emerging pattern; not yet confirmed |

Target: 10-15 items (~10 min read).

Done when: items structured with tier, title, summary, verdict, source link.
Fail: fewer than 5 quality items → tell user, offer to expand source list.

### Stage 4: Render

Load `assets/brief-template.html`.

1. Replace template markers with real content (see template comments)
2. Write rendered HTML to a temporary local file
3. Publish it with:
   `omp html-serve publish <tmp.html> --to ai-daily/<date>-daily-ai-brief.html --source daily-ai-brief --tag ai --tag daily-brief` (add 1-3 extra `--tag` for the day's dominant topics, e.g. `--tag agent`)
4. Generate Markdown archive under `$HTML_SERVE_DATA_DIR/ai-daily/` (`.md` extension)
5. Tell user both returned URLs: `localhost_url` and `tailscale_url`

`<date>` = `YYYY-MM-DD`. Output directory is always `ai-daily/`, independent of current project.

Done when: HTML published through `omp html-serve publish`, and both URLs are given to user.

## Hard Gate

| Condition | Action |
|---|---|
| No sources reachable | Abort, tell user to check network/web-operator |
| Fewer than 3 items pass editorial filter | Warn user, offer to lower threshold or expand sources |
| Template file missing | Abort, tell user to reinstall skill |
| `omp html-serve publish` reports missing `HTML_SERVE_DATA_DIR` | Ask user to configure `docker/html-serve/.env` or export `HTML_SERVE_DATA_DIR`; do not write to a hardcoded path. |
| html-serve container not running | Tell user: `omp container up html-serve` |
