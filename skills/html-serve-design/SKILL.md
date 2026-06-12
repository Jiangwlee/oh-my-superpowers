---
name: html-serve-design
description: >-
  Use when designing or upgrading another skill's html-serve output page:
  analyze the target skill's result structure, prototype the page on
  html-serve, iterate with browser feedback, and package the approved HTML
  template back into the target skill. Trigger when a user asks to add an HTML
  report page, publish page, preview page, result page, or html-serve template
  for a skill. Do NOT use for routine execution of an existing skill template.
---

# html-serve-design

Design a target skill's html-serve result page. This is a development-time
skill: create or improve the target skill's template and instructions, then
leave routine publishing to that target skill.

## Workflow

1. **Inspect target skill** - Read the target skill's `SKILL.md`, relevant
   `references/`, existing `assets/`, and current result files.
2. **Model the result** - Identify the target skill's stable output fields,
   source files, reader goal, and what should stay outside the HTML page.
3. **Choose page pattern** - Read `references/page-patterns.md` and select one
   pattern. If a new pattern is needed, justify it before creating it.
4. **Prototype on html-serve** - Read `references/publishing-contract.md` and
   `references/prototype-loop.md`, adapt `assets/prototype-workbench.html`,
   publish it to html-serve, and ask the user to review the browser page.
5. **Iterate** - Apply user feedback from the workbench export or chat. Repeat
   until the page structure, density, and visual tone are accepted.
6. **Package into target skill** - Copy the approved template into the target
   skill's `assets/`, then update the target skill's own reporting/publishing
   references so it can generate the page during normal runs.
7. **Validate** - Check the final template against
   `references/quality-checklist.md` and run the target skill's relevant static
   tests or validation commands.

## Required References

| Need | Read |
|---|---|
| html-serve path, URL, and prototype publishing rules | `references/publishing-contract.md` |
| Page type selection and output packaging | `references/page-patterns.md` |
| Visual style and anti-slop rules | `references/visual-system.md` |
| Browser preview and feedback loop | `references/prototype-loop.md` |
| Final self-check before handing off | `references/quality-checklist.md` |

## Assets

| Asset | Use |
|---|---|
| `assets/prototype-workbench.html` | Adapt first when designing a new page template. Publish this draft to html-serve for browser review. |
| `assets/report-template.html` | Starter for long-form report pages such as deep-research final reports. Copy into the target skill only after adapting it. |
| `assets/brief-template.html` | Starter for recurring summaries, digest pages, and action-first briefs. |
| `assets/review-template.html` | Starter for findings pages with severity, file/path metadata, and recommended actions. |
| `assets/index-template.html` | Starter for html-serve artifact catalogs and namespace indexes. |

## Hard Gates

| Condition | Action |
|---|---|
| Target skill is unknown | Ask which skill is being designed. |
| Target skill output shape is unclear | Inspect its files or ask for a sample output before designing. |
| The task is only routine publishing with an existing template | Do not use this skill; the target skill should execute its own template. |
| Prototype was not viewed in a browser | Do not package the final template yet. Publish a workbench page first. |
| Template would depend on this skill at runtime | Stop. Copy the final template and instructions into the target skill instead. |
| Personal paths, LAN IPs, or Tailscale IPs appear in committed files | Remove them. Use env vars and relative URL derivation. |

## Output Contract

The final handoff must name:

- The target skill files created or changed.
- The html-serve prototype URL used for review.
- The target skill asset that now owns the final template.
- The target skill reference that documents generation and publishing.
