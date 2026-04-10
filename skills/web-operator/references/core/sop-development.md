# SOP Development Workflow

This file explains how to develop a new site-specific SOP inside this skill.
Input is a new browser task such as search, list filtering, or post extraction.
Output is a stable workflow reference plus reusable scripts under `../scripts/`.
The public sections are scope design, page inspection, extraction design,
script structure, validation, deployment, and maintenance guidance.

Use this document when you want to add another website workflow like the
existing `x.com`, `reddit.com`, or `tgb.cn` integrations.

## Goal

The objective is not just to solve one browsing task once. The objective is to
turn a recurring browsing task into:

- a documented SOP
- one or more reusable scripts
- a stable place in the skill index

That keeps future runs out of the "rewrite ad hoc eval every time" trap.

## Design principles

- Prefer workflow scripts over repeated one-off `eval` snippets.
- Keep `cdp.mjs` as the generic browser-control layer.
- Put site-specific logic in separate helper and workflow scripts.
- Put procedural guidance in `references/`, not in `SKILL.md`.
- Validate against a real open tab before declaring the SOP stable.
- Prefer stable URL navigation over UI clicking when the destination URL is known.
- Treat page readiness and extraction logic as separate problems.

## Standard development flow

### 1. Define the exact SOP boundary

Before touching code, lock down:

- the input
- the output fields
- the default time window or result limit
- what is explicitly out of scope

Examples:

- `x.com` search:
  input is a query, output is result summaries, not full threads
- Reddit post reader:
  input is one post URL, output is main post plus visible comments, not expanded threads
- Taoguba follow feed:
  input is a time window, output is recent followed-content updates, not pagination

If this step is vague, the scripts will drift.

### 2. Inspect a real page first

Start from an already open tab when possible.

Typical sequence:

```bash
scripts/cdp.mjs list
scripts/cdp.mjs snap <target>
scripts/cdp.mjs eval <target> '<small probe>'
```

Use `snap` to understand the accessibility structure and page landmarks.
Use short `eval` probes to confirm:

- URL patterns
- link patterns
- time string formats
- whether the content is in stable DOM nodes or only in visible text flow

Do not start by writing the final extractor. First discover the page shape.

### 3. Separate navigation from extraction

Many failures come from mixing these two concerns.

- Navigation question:
  how do we land on the correct page reliably?
- Extraction question:
  once there, how do we read the content reliably?

Preferred order:

1. decide the stable destination URL
2. decide how to detect that the visible content is ready
3. only then write extraction logic

Examples:

- `x.com`:
  direct `nav` to `https://x.com/search?q=...`
- Reddit:
  `Page.navigate` plus explicit waits, because idle/load completion can be noisy
- Taoguba:
  tolerant navigation plus waits on visible text or content cards

### 4. Choose the right extraction strategy

There are three common patterns:

- DOM-anchored extraction
  Best when stable elements exist, for example `article`, `div.superM_content`, or `a[href*=...]`
- text-flow extraction
  Best when the page renders visibly but the DOM structure is noisy or unstable
- hybrid extraction
  Use DOM to locate the right region, then parse text lines from that region

Examples from this skill:

- `x.com`
  mostly DOM-anchored
- Reddit comments
  text-flow parsing from visible page lines
- Taoguba follow feed
  DOM card selection plus line parsing inside each card

### 5. Create the file set in the right order

For a new site, add files in this order:

1. `references/sites/<site>/workflows.md`
2. `scripts/sites/<site>/common.sh` (uses `scripts/core/common.sh`)
3. one or more workflow scripts
4. index links in `SKILL.md` and `references/core/index.md`

Recommended shape:

```text
references/sites/<site>/workflows.md
scripts/sites/<site>/common.sh
scripts/sites/<site>/search.sh
scripts/sites/<site>/open-post.sh
```

The helper script should own:

- **target selection** (via `find_or_create_tab` from `core/common.sh`)
- tolerant navigation
- readiness checks
- site-specific CDP wrappers

The workflow scripts should own:

- site-specific extraction logic
- CLI arguments
- default limits/windows
- output schema

#### Using the Shared Core Library

All site `common.sh` files should source the shared helpers:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../core/common.sh"
```

Then implement `*_find_target()` using `find_or_create_tab`:

```bash
example_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi
  
  # Automatically finds existing example.com tab or creates new one
  find_or_create_tab "https://www.example.com" "example.com"
}
```

This provides automatic tab lifecycle management without code duplication.

### 6. Keep output schemas explicit

Each workflow script should return stable JSON.

Do not make the caller infer structure from prose.

Good examples:

```json
{
  "title": "...",
  "author": "...",
  "time": "...",
  "text": "...",
  "url": "..."
}
```

```json
[
  {
    "title": "...",
    "summary": "...",
    "url": "..."
  }
]
```

If the schema is going to be used repeatedly, document it in the corresponding
workflow reference file.

### 7. Validate with isolation

Since each site workflow now manages its own dedicated tab (via `find_or_create_tab`), race conditions between different sites are eliminated. However, be aware of these constraints:

**Same-site serialization**: Multiple scripts for the same site will share the same tab (by design). If you must run multiple searches for one site in parallel, stagger them with delays.

**CDP connection pool**: Chrome's DevTools server has limits. Avoid launching more than ~5 concurrent scripts even across different sites to prevent WebSocket connection timeouts.

### 8. Debug with the smallest possible probe

When a workflow fails, do not immediately rewrite the whole script.

Instead, isolate the failure:

- is navigation wrong?
- is readiness detection wrong?
- is the selector wrong?
- is time parsing wrong?
- is text cleaning wrong?

Use tiny probes like:

```bash
scripts/cdp.mjs eval <target> 'location.href'
scripts/cdp.mjs eval <target> 'document.querySelectorAll("article").length'
scripts/cdp.mjs eval <target> '<slice a small text window>'
```

This was the fastest way to fix:

- stale websocket resolution in `cdp.mjs`
- Reddit comment parsing
- Taoguba follow-card readiness

## Readiness strategy checklist

Do not assume `nav` completion means page readiness.

Pick one of these:

- selector wait:
  when a stable node must appear
- text wait:
  when visible text is more reliable than DOM shape
- URL wait:
  when navigation itself is asynchronous or noisy

Often the stable pattern is:

1. navigate
2. wait for URL pattern
3. wait for selector or text
4. extract

## Time filtering checklist

For list SOPs with time windows:

- identify the exact string format shown on the page
- decide whether the page includes a year
- convert to local browser time
- compare against a numeric cutoff

Examples:

- `x.com`
  often no absolute time needed for search summaries
- Reddit
  relative strings like `1mo ago`, `10d ago`, `3h ago`
- Taoguba follow feed
  full timestamps like `2026-03-18 22:41:25`
- Taoguba `jinghua`
  month-day plus minute, so the script assumes the current year

## Cleaning rules

Extraction usually succeeds before cleaning succeeds.

Expect a second pass for:

- author/title duplication
- translation labels
- view counters
- footer actions
- reply-floor bleed into main content

Do not overfit cleaning until you have one or two real examples from the site.

## Deployment workflow

After the repository version is stable:

1. sync the updated skill into `~/.agents/skills/web-operator/`
2. verify the deployed file layout
3. prefer real script execution over visual inspection only

Typical sync command:

```bash
rsync -a "$REPO_ROOT/skills/web-operator/" /home/bruce/.agents/skills/web-operator/
```

## Minimal acceptance checklist

A new SOP is ready when all of the following are true:

- the workflow boundary is documented
- the reference index links to the new workflow doc
- the helper script exists if the site needs repeated logic
- the workflow scripts return structured JSON
- each workflow has been run successfully on a real open tab
- the deployed skill under `~/.agents/skills/` matches the repository version

## Recommended pattern for future sites

When adding a new site, follow this sequence exactly:

1. define scope and output schema
2. inspect a live page with `list`, `snap`, and tiny `eval`
3. determine URL pattern and readiness signal
4. write `scripts/sites/<site>/common.sh`
5. write one workflow script at a time
6. validate serially on real tabs
7. add reference docs and index links
8. sync to `~/.agents/skills/`

That is the workflow used to build the existing `x.com`, `reddit.com`, and
`tgb.cn` SOPs in this skill.

## Expected Project Structure

Each supported site should eventually have:

- scripts under `scripts/sites/<site>/`
- references under `references/sites/<site>/`
- tests under `tests/sites/<site>/`

Test commands:

- `omp web-operator test list`
- `omp web-operator test core`
- `omp web-operator test site <name>`
- `omp web-operator test all`

## Definition Of Done For New Site Support

New site support is not complete unless it includes:

- workflow scripts
- a site reference document
- at least one smoke test
- registration in the unified test runner
