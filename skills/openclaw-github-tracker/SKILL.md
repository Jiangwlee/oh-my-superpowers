---
name: openclaw-github-tracker
description: Use when tracking GitHub trending repos, managing watchlists, or analyzing projects for OpenClaw workflows.
version: "1.1.0"
---

# OpenClaw GitHub Tracker

Track GitHub trending repositories, maintain watchlists, generate project dossiers, and monitor updates.

## Prerequisite Check (REQUIRED)

**STOP and resolve before proceeding:**

1. **GitHub CLI**: `command -v gh` → Install if missing: https://cli.github.com
2. **Authentication**: `gh auth status` → Run `gh auth login` if not authenticated
3. **Python 3.10+**: `python3 --version` → Required for scripts
4. **Browser availability**: Confirm OpenClaw browser tool is available

**If any check fails, stop and provide installation steps. Do not continue.**

## Guardrails (HARD CONSTRAINTS)

<HARD-GATE>

### Iron Laws

**NO watchlist additions WITHOUT explicit user confirmation FIRST.**
- ❌ **WRONG**: "Adding this trending repo to your watchlist..."
- ✅ **CORRECT**: "Would you like to add owner/repo to watchlist? [yes/no]"

**NO trending data WITHOUT GitHub daily page + browser FIRST.**
- ❌ **WRONG**: Using `gh search repos --sort stars` for "today's trending"
- ✅ **CORRECT**: Open browser to https://github.com/trending, read daily tab

### SPA Trap Warning

⚠️ **GitHub is a Single Page Application (SPA).** Direct HTTP requests (curl, wget, urllib, web_fetch) only return the JavaScript shell, NOT the actual content. **Always use browser for Trending collection.**

### Daily vs Weekly Verification

- ❌ **WRONG URL**: `github.com/trending/weekly` or `github.com/trending/monthly`
- ✅ **CORRECT URL**: `github.com/trending` (this shows daily trending)

**Before extracting data:**
1. Check browser URL bar shows `/trending` NOT `/trending/weekly` or `/trending/monthly`
2. Verify page header or tab indicates "Today" or "Daily"

### Authority Statements

- **YOU MUST** ask before adding to watchlist — no exceptions
- **Always confirm** with user before destructive operations
- **Never assume** implicit permission from context

### Common Rationalizations (BLOCKED)

| Excuse | Reality |
|--------|---------|
| "The user mentioned this repo earlier..." | Mention ≠ permission to add to watchlist |
| "This is clearly trending/high-value..." | Value assessment is user's prerogative |
| "I'll add it and they can remove later..." | Opt-out violates user-driven principle |
| "Let me just list the top 5 most starred..." | MUST include ALL repositories, not filtered subset |
| "This project has 10k stars so it must be good..." | Functionality matters, not just popularity metrics |

</HARD-GATE>

## Extraction Protocols (Context-Specific)

### Trending Data Collection — BROWSER ONLY

**NO FALLBACK for Trending**: Trending data MUST come from browser at `github.com/trending`. There is no API equivalent for GitHub's trending algorithm.

**If browser fails**:
- Stop and report: "Cannot fetch trending — browser unavailable"
- Do NOT substitute with search results or starred repos
- Ask user to retry later

### Repository Metadata — API with Fallback

For repo details, analysis, and updates:

1. **Primary**: GitHub API via `gh api`
2. **Fallback**: `gh repo view --json`
3. **Last resort**: Browser (if API quota exceeded)

**Triggers for fallback**:
- 401/403 → Check auth, fallback to `gh repo view`
- 429 → Apply back-off, then try browser
- Network timeout → Retry once, then fail

## Rate Limit Protection

**Mandatory pauses between API calls**:
- Minimum 1 second between sequential calls
- Burst limit: max 10 calls without pause
- 429 response: read `x-ratelimit-reset`, wait until timestamp

**Back-off strategy**:
- First 429: wait 60 seconds
- Second 429: wait 5 minutes
- Third 429: stop and report "Rate limit exceeded, resume after [timestamp]"

## Workflow & Data Boundaries

Each workflow step produces specific artifacts:

| Step | Input | Output | Tool |
|------|-------|--------|------|
| Fetch Trending | None | `briefs/daily/YYYY-MM-DD.md` | Browser |
| Add to Watchlist | User confirmation | `watchlist/watchlist.json` | Script |
| Deep Analysis | `owner/repo` string | `projects/<owner>__<repo>/profile.md` + `snapshots/*.json` | Script |
| Track Updates | Existing snapshot | `projects/<owner>__<repo>/updates/YYYY-MM-DD.md` | Script |

**Tool boundaries**:
- **Browser ONLY**: Trending collection (GitHub SPA requirement)
- **gh CLI preferred**: All repo operations (API, clone, metadata)
- **Scripts**: Watchlist management, analysis, tracking

## Standard Workflow

### Step 1: Fetch Daily Trending

**Input**: None  
**Output**: `briefs/daily/YYYY-MM-DD.md`  
**Tool**: Script + OpenClaw browser

**ALWAYS run the script first to get instructions, then execute browser operations.**

```bash
# Step 1: Get browser instructions
python3 .agents/skills/openclaw-github-tracker/scripts/fetch_trending.py \
  --memory-root .memory

# Step 2: Use OpenClaw browser to extract data per script instructions
# (Browser tool will be invoked here)

# Step 3: Generate brief with extracted data
python3 .agents/skills/openclaw-github-tracker/scripts/fetch_trending.py \
  --memory-root .memory \
  --data-json '[{"repo":"owner/repo","what_it_does":"..."},...]'
```

**Script enforces:**
- URL hardcoded to `github.com/trending` (daily only)
- Minimum 10 repositories (fails if incomplete)
- No duplicate repositories
- Functional descriptions (not just popularity metrics)

### Step 2: Add to Watchlist

**Input**: User confirmation  
**Output**: Updated `watchlist/watchlist.json`  
**Tool**: Script

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/watchlist.py \
  add owner/repo \
  --memory-root .memory
```

### Step 3: First-Time Deep Analysis

**Input**: `owner/repo`  
**Output**: `projects/<owner>__<repo>/profile.md` + snapshot  
**Tool**: Script

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/analyze_project.py \
  owner/repo \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json
```

### Step 4: Track Updates

**Input**: Existing project snapshot  
**Output**: `projects/<owner>__<repo>/updates/YYYY-MM-DD.md`  
**Tool**: Script

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/track_updates.py \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json
```

### Step 5: Pipeline (Steps 3-4 automation)

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/run_pipeline.py \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json \
  --analyze-mode new
```

**TERMINAL STATE**: Analysis artifacts written to `.memory/github-tracker/projects/`. Do NOT invoke additional skills unless user requests.

## Output Format Reference

When generating files, read `references/formats.md` for exact schema.

## Analysis Scope

Each project profile includes:

- Architecture signals (repo layout + branch signals)
- Technology stack and language mix
- Main functional modules (top-level structure + README cues)
- Roadmap signals (README roadmap section + milestones/releases)
- License and compliance basics
- Baseline metrics snapshot for future diffs

## Required Dependencies

| Skill/Tool | Purpose | Required |
|------------|---------|----------|
| OpenClaw browser | Trending page access | Yes |
| gh CLI | GitHub API operations | Yes |
| Python 3.10+ | Script execution | Yes |

## Pre-Execution Checklist

Before completing any task:
- [ ] Prerequisite checks passed
- [ ] Watchlist changes have explicit user confirmation
- [ ] Trending data sourced from browser (not API/search)
- [ ] **Daily Brief**: URL is `/trending` (NOT `/trending/weekly`)
- [ ] **Daily Brief**: item_count ≥ 10 (ALL repositories included, not filtered subset)
- [ ] **Daily Brief**: Each repo includes "What it does" functional description
- [ ] **Daily Brief**: Watchlist recommendations based on functionality, not just star count
- [ ] Output follows format schema in references/formats.md
- [ ] All artifacts written to correct paths

## Directory Layout

Initialize once:

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/bootstrap_layout.py \
  --memory-root .memory
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

## Configuration

Optional proxy (for urllib fallback):

```bash
export GITHUB_TRACKER_HTTP_PROXY="http://127.0.0.1:10801"
export GITHUB_TRACKER_HTTPS_PROXY="http://127.0.0.1:10801"
export GITHUB_TRACKER_NO_PROXY="localhost,127.0.0.1"
```

Or edit `.agents/skills/openclaw-github-tracker/config.json`.
