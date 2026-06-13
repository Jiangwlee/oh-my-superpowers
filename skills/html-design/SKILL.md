---
name: html-design
description: >-
  Use when designing a polished static HTML page prototype and its DESIGN.md:
  clarify the user's page scenario, choose an information organization model,
  search DESIGN.md references, create multiple adjustable prototypes, publish
  them to html-serve, and iterate from user feedback. Do NOT use for routine
  publishing of an already-approved HTML template.
---

# html-design

Design a style-conscious HTML page prototype and a matching `DESIGN.md`.
Use this skill for prototype exploration, not for routine report generation.

## CLI

```bash
omp html-design compile [--source PATH] [--output PATH]
omp html-design search <keywords...> [--index PATH] [--limit N]
omp html-design init [--slug SLUG] [--root PATH]
```

| Command | Purpose |
|---|---|
| `compile` | Scan design-system `DESIGN.md` files and write a searchable index to `assets/design-index.json`. |
| `search` | Find matching `DESIGN.md` paths by scene, style, product category, or other keywords. |
| `init` | Create a temporary workspace for the current design task. |

## Workflow

1. **Clarify scenario** - Identify page purpose, audience, content shape,
   interaction needs, target viewport, and any brand constraints.
2. **Model the information** - Read `references/information-organization.md`
   and choose one primary organization model plus any secondary support model.
3. **Initialize workspace** - Run `omp html-design init --slug <task-slug>` and
   use the returned directory for copied references, prototypes, and exports.
4. **Find references** - Run `omp html-design search <scenario style keywords>
   --limit 5`. If the index is missing or stale, run `omp html-design compile`
   first.
5. **Copy and tune references** - Copy the five closest `DESIGN.md` files into
   the temporary workspace, then create one task-specific `DESIGN.md` variant
   for each direction.
6. **Generate prototypes** - Create one adjustable HTML prototype per
   `DESIGN.md` direction. Use `references/prototype-loop.md` and adapt
   `assets/prototype-workbench.html`; expose controls for the page decisions
   that matter.
7. **Publish for review** - Use `references/publishing-contract.md` to publish
   prototypes to html-serve and give the user the preferred review URL.
8. **Iterate and finalize** - Apply user feedback, keep the chosen prototype
   and final `DESIGN.md`, and remove rejected temporary directions from the
   handoff unless the user asks to keep them.
9. **Validate** - Check the result against
   `references/quality-checklist.md` before declaring the design ready.

## Required References

| Need | Read |
|---|---|
| Information organization models and selection rules | `references/information-organization.md` |
| html-serve path, URL, and prototype publishing rules | `references/publishing-contract.md` |
| Prototype controls, browser loop, and export contract | `references/prototype-loop.md` |
| Visual style and anti-slop rules | `references/visual-system.md` |
| Final self-check before handoff | `references/quality-checklist.md` |

## Assets

| Asset | Use |
|---|---|
| `assets/design-index.json` | Compiled index of external design-system `DESIGN.md` files. Regenerate with `omp html-design compile`. |
| `assets/prototype-workbench.html` | Adapt for each candidate page direction; publish drafts to html-serve for review. |
| `assets/report-template.html` | Starter for long-form report pages. |
| `assets/brief-template.html` | Starter for recurring summaries, digest pages, and action-first briefs. |
| `assets/review-template.html` | Starter for findings pages with severity, metadata, and recommended actions. |
| `assets/index-template.html` | Starter for artifact catalogs, directories, and namespace indexes. |

## Hard Gates

| Condition | Action |
|---|---|
| User need or page scenario is unclear | Ask for the missing scenario detail before prototyping. |
| Information organization is unspecified | Choose and name a primary model before writing layout or CSS. |
| Fewer than five relevant `DESIGN.md` references are available | Explain the gap and use the closest available references; do not fabricate paths. |
| Prototype has not been published or viewed | Do not call the direction final. Publish a workbench page first. |
| The task only needs routine publishing from an existing template | Do not use this skill; use the owning workflow instead. |
| Personal paths, LAN IPs, or Tailscale IPs appear in committed files | Remove them. Use env vars and relative URL derivation. |

## Output Contract

The final handoff must name:

- The temporary workspace path.
- The five reference `DESIGN.md` files considered.
- The chosen information organization model.
- The html-serve prototype URL used for review.
- The final HTML prototype file and final `DESIGN.md`.
- The validation command or checklist used.
