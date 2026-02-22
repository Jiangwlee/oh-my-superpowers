---
name: github-researcher
description: Use when collecting GitHub daily trending, analyzing specific repositories, and tracking watchlist repository updates over time.
---

# GitHub Researcher

## Purpose

Run a repeatable GitHub research workflow:
1. Collect daily trending from GitHub Trending using browser tool.
2. Maintain a user-approved watchlist.
3. Download repository code and run deep analysis (`claude` -> `codex` -> Openclaw current model).
4. Track updates for watched repositories.

## Hard Rules

1. Trending must be collected from browser view of `https://github.com/trending` (daily).
2. Do not auto-add watchlist items without explicit user confirmation.
3. Deep analysis engine order is fixed: `claude` first, then `codex`, then Openclaw current model.
4. Repository code must be cloned locally before deep analysis.
5. `claude` deep analysis requires logged-in auth (`claude auth status`).
6. If network access fails, report failure clearly and suggest user configure proxy/network.

## Storage Layout

```text
.memory/github-researcher/
  briefs/daily/
  indexes/project-index.jsonl
  watchlist/watchlist.json
  projects/<owner>__<repo>/
    profile.md
    snapshots/
    updates/
```

## Workflow

### 1) Daily Trending (browser only)

- Open browser tool and go to `https://github.com/trending`.
- Use daily ranking visible on page to produce brief file:
  - `.memory/github-researcher/briefs/daily/YYYY-MM-DD.md`
- Use format template in `references/formats.md`.
- Close browser

### 2) Bootstrap layout

```bash
python3 scripts/bootstrap_layout.py --memory-root .memory
```

### 3) Watchlist operations

```bash
python3 scripts/watchlist.py add cli/cli --memory-root .memory
python3 scripts/watchlist.py list --memory-root .memory
```

### 4) Deep analyze one repository (claude first, codex fallback)

```bash
python3 scripts/analyze_repo.py cli/cli --memory-root .memory --mode deep
```

Outputs:
- Local code cache under `.memory/github-researcher/cache/<owner>__<repo>/`
- Deep report: `.memory/github-researcher/projects/<owner>__<repo>/updates/YYYY-MM-DD-deep-analysis.md`
- Profile and snapshot for follow-up analysis
- Deep report must include:
  - `## 分层架构图` (Mermaid)
  - `## 代码目录结构图` (text tree)

If script-level LLM engines both fail, fallback to Openclaw current model in chat:
1. Keep using the same cloned code cache path.
2. Ask Openclaw model to read key files and produce the deep analysis report with the same report sections.
3. Save output to `projects/<owner>__<repo>/updates/YYYY-MM-DD-deep-analysis.md`.

### 5) Track updates for watchlist

```bash
python3 scripts/track_updates.py --memory-root .memory
```

## Key Commands (tested examples)

Use these commands before and during deep analysis.

```bash
# Preflight: Claude auth status
claude auth status

# Preflight: Codex availability
codex --version

# Deep analysis command (claude first, codex fallback)
python3 scripts/analyze_repo.py cli/cli --memory-root .memory --mode deep
```

## Failure Handling

If clone or LLM analysis fails, return a clear message like:

- What failed (`git clone`, `claude`, or `codex`)
- Which repo failed
- Next action suggestion:
  - First, ask user to check network/proxy settings and retry.
  - If both `claude` and `codex` still fail, continue analysis with Openclaw current model on the cloned code.

Example suggestion:

- "GitHub request failed. Please verify your network can access github.com. If you are behind a restricted network, configure a local proxy and retry."

## References

- Output formats: `references/formats.md`
- Scripts: `scripts/*.py`
