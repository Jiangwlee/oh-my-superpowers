---
name: llm-wiki
description: >-
  Use when working with a Karpathy-style markdown wiki managed through `omp wiki`,
  including ingesting raw sources, synthesizing wiki pages, navigating the
  compiled wiki, linting knowledge quality, or archiving outputs back into the wiki.
  Do NOT use when the task is ordinary web research, repo code search, or reading
  raw documents directly without using the wiki workflow.
---

# llm-wiki

Use this skill when the task should follow the Karpathy LLM Wiki workflow instead of ad-hoc note taking or direct raw-document reading.

## Skill Model

- `omp wiki` is the **data plane**: init, ingest, nav, lint.
- `llm-wiki` (this skill) is the **SOP**: decides when and how to synthesize.
- The **caller agent** does the synthesis: it reads `raw/*.md` and writes `wiki/**/*.md` using its own tools.
- The system is filesystem-first: `raw/` for inputs, `wiki/` for curated markdown knowledge pages.

## Unified Entry

```bash
omp wiki init
omp wiki ingest
omp wiki nav
omp wiki lint
```

If you are unsure about arguments, run `omp wiki <subcommand> --help`.

Synthesis and page reading are **not** CLI commands. The caller agent does them directly using its own Read/Write tools, following this skill's SOP.

## Core Rules

1. **Start from the wiki, not raw**
   Run `omp wiki nav` first, then read `wiki/index.md`, `wiki/sources/`, `wiki/concepts/`, or `wiki/maps/`.
2. **Ingest before reasoning from new material**
   New URLs, files, or notes go through `omp wiki ingest` before you rely on them.
3. **Synthesize when `pending_synthesis` is non-empty**
   After ingest, `omp wiki nav --json` reports `pending_synthesis`: raw files without a `wiki/sources/` page. Run the compile SOP (`references/compile.md`) to cover them.
4. **Lint when structure or truth may have drifted**
   Run `omp wiki lint` when the wiki has grown, links may be stale, or answers look unstable.
5. **Archive valuable outputs back**
   Long-lived reports, summaries, or notes should be written back into the wiki workflow instead of staying only in chat.

## Query Discipline

- Prefer compiled pages over raw material.
- Use `wiki/sources/` for evidence verification.
- Use `wiki/concepts/` and `wiki/maps/` for synthesis when available.
- If the compiled wiki lacks enough material, say so clearly instead of compensating by treating `raw/` as the default query layer.

## When To Load References

- Load `references/cli.md` when you need flags or argument shapes beyond `--help`.
- Load `references/workflow.md` at the start of a fresh wiki session or when query discipline is unclear.
- Load `references/compile.md` + `references/source-template.md` when `pending_synthesis` is non-empty.
- Load `references/concept-template.md` when creating a cross-source concept page.
- Load `references/map-template.md` when creating a reading-path map.
- Load `references/linting.md` when `omp wiki lint` output is unclear or you need to resolve a reported issue.
- Load `references/archive.md` when deciding whether to persist an output back into the wiki.
