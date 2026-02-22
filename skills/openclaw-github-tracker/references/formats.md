# Output Formats

**Version**: 1.1.0  
**Last Updated**: 2026-02-22  
**Change Policy**: Backward compatible additions only (new fields, new optional sections). Breaking changes require major version bump.

## Table of Contents

- [Format Versions](#format-versions)
- [1. Daily Brief](#1-daily-brief-briefsdailyyyyy-mm-ddmd)
- [2. Project Profile](#2-project-profile-projectsowner__repoprofilemd)
- [3. Update Note](#3-update-note-projectsowner__repoupdatesyyyy-mm-ddmd)
- [4. Global Index](#4-global-index-indexesproject-indexjsonl)
- [Schema Change Log](#schema-change-log)

## Format Versions

New files SHOULD include format version in frontmatter:

```yaml
format_version: "1.1.0"
```

### Version Compatibility Rules

| Change Type | Rule | Example |
|-------------|------|---------|
| **Patch** (1.0.x) | Bug fixes, clarifications | Fix typo in field description |
| **Minor** (1.x.0) | Add optional fields/sections | Add `homepage_url` to profile |
| **Major** (x.0.0) | Remove/rename required fields | Remove `stars` from profile |

**Backward compatibility guarantee**: 
- Scripts reading format 1.0.0 MUST successfully parse files written in 1.1.0 (ignoring unknown fields)
- Files written by 1.0.0 scripts (without `format_version`) remain valid in 1.1.0
- `format_version` is optional to avoid breaking existing script outputs

## 1. Daily Brief (`briefs/daily/YYYY-MM-DD.md`)

**MUST be daily data** — verify URL is `/trending` not `/trending/weekly`.

```md
---
type: github_trending_brief
format_version: "1.1.0"
date: YYYY-MM-DD
source: https://github.com/trending
since: daily
item_count: 25
---

# GitHub Trending Brief (YYYY-MM-DD)

## Complete Repository List

**ALL {{item_count}} repositories from GitHub Trending Daily:**

### 1. owner/repo-name
**What it does**: [One-line functional description — what problem does this solve?]
**Tech stack**: [Primary language + key frameworks if visible]
**Key insight**: [Why trending today — new release, viral feature, solves current pain point?]
**Stars**: [current count] | **Today**: [+stars today]

### 2. owner/another-repo
**What it does**: [Functional description]
[... continue for ALL repositories]

## Summary by Category
| Category | Repos | Common Themes |
|----------|-------|---------------|
| AI/ML | 5 | LLM tools, inference optimization |
| DevTools | 4 | CLI utilities, developer experience |
| ... | ... | ... |

## Candidate Actions
- **Add to watchlist**: owner/repo — [specific reason based on functionality, not just popularity]
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `github_trending_brief` |
| `date` | string | ISO date `YYYY-MM-DD` |
| `source` | string | Data source URL |
| `since` | enum | **MUST be `daily`** — verify URL is `/trending` not `/trending/weekly` |
| `item_count` | integer | **MUST be ≥ 10** — if < 10, re-read the page and verify you're on the Daily tab |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `format_version` | string | Schema version (e.g., `1.1.0`). **Recommended for new files**; existing scripts without it remain valid. |

### Content Requirements

**Functional Focus** (NOT popularity metrics):
- Each repository MUST include "What it does" describing the problem it solves
- Tech stack should mention practical use cases
- "Why trending" should explain functional significance, not just star count
- Candidate actions should reference specific capabilities, not "high stars"

**Completeness**:
- Include ALL repositories from the trending page (typically 25-30)
- Do not filter or summarize down to "top picks"
- If brief feels too long, that's correct — trending has many repos

## 2. Project Profile (`projects/<owner>__<repo>/profile.md`)

```md
---
type: github_project_profile
format_version: "1.1.0"
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

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `github_project_profile` |
| `repo` | string | Full repo name `owner/repo` |
| `analyzed_at` | ISO timestamp | Analysis completion time |
| `default_branch` | string | Primary branch name |
| `license` | string | License identifier |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `format_version` | string | Schema version. **Recommended for new files**; existing scripts without it remain valid. |

## 3. Update Note (`projects/<owner>__<repo>/updates/YYYY-MM-DD.md`)

```md
---
type: github_project_update
format_version: "1.1.0"
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

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `github_project_update` |
| `repo` | string | Full repo name |
| `generated_at` | ISO timestamp | Update generation time |
| `compared_to_snapshot` | ISO timestamp | Baseline snapshot timestamp |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `format_version` | string | Schema version. **Recommended for new files**; existing scripts without it remain valid. |

## 4. Global Index (`indexes/project-index.jsonl`)

One JSON object per line:

```json
{
  "format_version": "1.1.0",
  "repo": "owner/repo",
  "slug": "owner__repo",
  "first_analyzed_at": "2026-02-16T12:00:00Z",
  "last_analyzed_at": "2026-02-16T12:00:00Z",
  "profile_path": "projects/owner__repo/profile.md",
  "last_update_path": "projects/owner__repo/updates/2026-02-16.md",
  "tags": ["ai", "agent"],
  "status": "active"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `repo` | string | Full repo name |
| `slug` | string | URL-safe identifier |
| `first_analyzed_at` | ISO timestamp | Initial analysis time |
| `last_analyzed_at` | ISO timestamp | Most recent analysis |
| `profile_path` | string | Relative path to profile |
| `status` | enum | `active`, `archived`, `removed` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `format_version` | string | Schema version. **Recommended for new files**; existing scripts without it remain valid. |
| `last_update_path` | string | Path to latest update note |
| `tags` | string[] | Category tags |

## Design Principles

- **Stable keys** for retrieval (`repo`, `slug`, timestamps)
- **Append/update compatible** for memory systems
- **Human docs (Markdown)** + **machine index (JSONL)**
- **Version-tagged** for schema evolution

## Schema Change Log

### 1.1.0 (2026-02-22)
- Added: `format_version` field as **optional** to all formats (backward compatible with existing script outputs)
- Added: Version compatibility rules documentation
- Added: Required/optional fields tables
- Changed: Daily Brief format now requires functional descriptions ("What it does") instead of metrics-focused tables
- Changed: `since` field in Daily Brief **MUST be `daily`** — enforced to prevent weekly/monthly confusion
- Changed: `item_count` in Daily Brief **MUST be ≥ 10** — enforced to ensure completeness
- Changed: Extraction protocols split: Trending (browser-only) vs Repo metadata (API with fallback)

### 1.0.0 (2026-02-16)
- Initial schema definition
- Daily Brief, Project Profile, Update Note, Global Index formats
