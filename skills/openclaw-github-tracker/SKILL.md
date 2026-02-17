---
name: openclaw-github-tracker
description: Use when building or running an OpenClaw workflow to discover GitHub trending repositories, maintain a watchlist, generate first-time deep project dossiers, and track important updates across followed repositories.
---

# OpenClaw GitHub Tracker

## Overview

Use this skill to run a repeatable GitHub project intelligence workflow for OpenClaw:

1. Open browser and collect GitHub Trending (daily) from page
2. Maintain a watchlist of interesting repositories
3. Generate first-time deep project dossiers
4. Track meaningful updates since the previous analysis
5. Keep a machine-friendly index for memory systems (including claude-mem)

## Principles

1. **Watchlist must be user-driven** - AI must NOT add projects to watchlist without explicit user permission. Always ask the user before adding.
2. **Prefer gh over direct urllib calls** - Use `gh` for GitHub API/clone operations whenever possible to reduce rate-limit risk.
3. **Trending source must be GitHub daily page data** - For "today hot projects", use `https://github.com/trending` (daily) data. Do not substitute with all-time/top-star search results.
4. **Trending collection must use browser** - AI must open `https://github.com/trending` in OpenClaw browser and read page data directly. Do not use regex HTML scraping scripts for trending collection.

## Directory Layout (claude-mem friendly)

Run once to initialize:

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/bootstrap_layout.py \
  --memory-root .memory
```

Optional proxy configuration (for urllib fallback paths):

Edit `.agents/skills/openclaw-github-tracker/config.json`:

```json
{
  "http_proxy": "http://127.0.0.1:7890",
  "https_proxy": "http://127.0.0.1:7890",
  "no_proxy": "localhost,127.0.0.1"
}
```

Generated structure:

```text
.memory/github-tracker/
  briefs/daily/
  indexes/project-index.jsonl
  trending/raw/
  watchlist/watchlist.json
  projects/<owner>__<repo>/
    profile.md
    snapshots/
    updates/
```

This layout is append-friendly (JSONL + Markdown), stable for retrieval, and easy for claude-mem ingestion.

## Standard Workflow

1. Fetch daily trending via browser:
Open OpenClaw browser, navigate to `https://github.com/trending`, and compile the brief from visible page rows (daily tab/page data).

2. Add repository to watchlist:

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/watchlist.py \
  add owner/repo \
  --memory-root .memory
```

3. First-time deep analysis:

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/analyze_project.py \
  owner/repo \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json
```

4. Track updates since last snapshot:

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/track_updates.py \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json
```

5. Run analysis + tracking pipeline (trending step remains manual/browser):

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/run_pipeline.py \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json \
  --analyze-mode new
```

## Analysis Scope

Each project profile includes:

- Architecture signals (repo layout + branch signals)
- Technology stack and language mix
- Main functional modules (top-level structure + README cues)
- Roadmap signals (README roadmap section + milestones/releases)
- License and compliance basics
- Baseline metrics snapshot for future diffs

## References

- Format definitions: `references/formats.md`
- Script entrypoints: `scripts/*.py`
