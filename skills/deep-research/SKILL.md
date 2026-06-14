---
name: deep-research
description: >-
  Use when a task requires systematic multi-round research across multiple
  angles, sources, and validation steps before producing a conclusion or
  report. Do NOT use when a quick ad-hoc search, a single-page summary, or a
  one-off fact lookup is enough.
---

# deep-research Skill

Turn open-ended research into an auditable loop: plan → broad search → deep read → validation → report.

Use for questions that need multiple angles, multiple sources, and explicit verification. Do not use for quick fact lookup, one-page summary, or casual search.

## Output Contract

A completed run must produce:

- `plan.md` with 3-6 tracked subquestions
- `reports/brief.md`
- `reports/full-report.md`
- `reports/report.html`
- Published HTML under `deep-research/` via `omp html-serve publish`
- `state.json` with sources and report paths

Do not declare the report complete if `reports/report.html` is missing, still contains `{{MARKER}}` placeholders, or has not been published/attempted with `omp html-serve publish`.

## Workflow

| Phase | Required action | Load |
|---|---|---|
| 0. Clarify | Create `plan.md`; define subquestions and scope. | `references/methodology.md` |
| 1. Explore | Map dimensions, terms, entities, and viewpoints. | `references/source-strategy.md` |
| 2. Deepen | Read high-value sources; write Pre-search Reasoning before each search. | `references/methodology.md` |
| 3. Validate | Add counterpoints, limits, alternatives, risks, and contradictions. | `references/source-strategy.md` |
| 4. Synthesize | Emit `[Round N Synthesis]`; update `plan.md`; decide continue/stop. | `references/stop-criteria.md` |
| 5. Report | Write Markdown reports, generate HTML, then publish to html-serve under `deep-research/`. | `references/reporting.md`, `references/html-reporting.md` |

Do not stop early when key full-text sources, opposing views, or limitation evidence are missing.

## CLI

```bash
omp deep-research <subcommand> [args]
```

| Command | Purpose |
|---|---|
| `init` | Create a workspace: `--topic`, `--slug`, `--mode`. |
| `build-report` | Write reports, render `reports/report.html`, and update `state.json`. |

Read `references/cli.md` before the first CLI call or when parameters are unclear.

## Publish Command

After `omp deep-research build-report` creates `reports/report.html`, publish the HTML report to the `deep-research/` directory:

```bash
omp html-serve publish /tmp/report.html --to deep-research/2026-06-13.html
```

In real runs, replace `/tmp/report.html` with the generated `reports/report.html` path and use the workspace/report name for the target file, for example:

```bash
omp html-serve publish "<workspace>/reports/report.html" --to "deep-research/<workspace-name>.html"
```

Return the `localhost_url` and `tailscale_url`. If publishing fails, report the error and still return the local `reports/report.html` path.

## Search Tool

Prefer `omp web-operator`:

- `search-multi` for 2-3 complementary platforms per round
- `read-url` for full text

Fallback to WebSearch / WebFetch only when `web-operator` fails. Do not hand-roll CDP or curl page scraping.

## Data

Default workspace root: `~/.local/share/oh-my-superpowers/deep-research/`. Override with `DEEP_RESEARCH_DATA_DIR`. Directory layout and `state.json` schema live in `references/workspace.md`.
