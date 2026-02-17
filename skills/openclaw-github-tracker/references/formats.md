# Output Formats

## 1. Daily Brief (`briefs/daily/YYYY-MM-DD.md`)

```md
---
type: github_trending_brief
date: YYYY-MM-DD
source: https://github.com/trending
since: daily|weekly|monthly
item_count: 20
---

# GitHub Trending Brief (YYYY-MM-DD)

## Top Highlights
- owner/repo: one-line value proposition + key signal

## Trend Table
| Rank | Repo | Lang | Stars | This Period | Why It Matters |
|---|---|---|---:|---:|---|

## Candidate Actions
- Add to watchlist: owner/repo (reason)
```

## 2. Project Profile (`projects/<owner>__<repo>/profile.md`)

```md
---
type: github_project_profile
repo: owner/repo
analyzed_at: YYYY-MM-DDTHH:MM:SSZ
default_branch: main
license: MIT
---

# owner/repo Dossier

## Executive Summary
- What problem it solves
- Current maturity signal

## Architecture Signals
- Monorepo/single-package cues
- Top-level directories and layering hints

## Technology Choices
- Primary language mix
- Framework/runtime cues from README or layout

## Main Modules
- module-name: responsibility

## Roadmap Signals
- README roadmap notes
- Milestones/releases trend

## License & Compliance
- SPDX and constraints

## Baseline Metrics
- Stars/Forks/Open issues/Recent release/Pushed at
```

## 3. Update Note (`projects/<owner>__<repo>/updates/YYYY-MM-DD.md`)

```md
---
type: github_project_update
repo: owner/repo
generated_at: YYYY-MM-DDTHH:MM:SSZ
compared_to_snapshot: YYYY-MM-DDTHH:MM:SSZ
---

# Update Digest: owner/repo

## Metric Changes
- stars: +123
- forks: +8
- open_issues: -4

## Important Activity
- Recent commits highlights
- New release(s)
- Milestone changes

## Why It Matters
- Potential impact for adoption, contribution, or architecture decisions
```

## 4. Global Index (`indexes/project-index.jsonl`)

One JSON object per line:

```json
{"repo":"owner/repo","slug":"owner__repo","first_analyzed_at":"2026-02-16T12:00:00Z","last_analyzed_at":"2026-02-16T12:00:00Z","profile_path":"projects/owner__repo/profile.md","last_update_path":"projects/owner__repo/updates/2026-02-16.md","tags":["ai","agent"],"status":"active"}
```

Design principles:

- Stable keys for retrieval (`repo`, `slug`, timestamps)
- Append/update compatible for memory systems
- Human docs (Markdown) + machine index (JSONL)
