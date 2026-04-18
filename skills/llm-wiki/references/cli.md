# CLI Reference

Use `omp wiki` as the single entrypoint. The CLI is a thin **data plane**; it does not generate content.

## Commands

- `omp wiki init`
  Initialize the global wiki home (`raw/`, `wiki/`, `state.json`).
- `omp wiki ingest <url-or-file>`
  Ingest a URL or local file into `raw/`.
- `omp wiki ingest --text --title <title>`
  Read stdin into `raw/`.
- `omp wiki nav [--json]`
  Show entrypoints, counts, and `pending_synthesis` (raw files without a `wiki/sources/` page).
- `omp wiki lint [--json]`
  Report structural issues in the compiled wiki (broken wikilinks, missing headings).

## Reading and writing wiki pages

The caller agent reads and writes `wiki/` files directly using its own tools
(for example the `Read`, `Write`, and `Edit` tools). There is no `omp wiki read`
or `omp wiki compile` command — synthesis is SOP-driven, not CLI-driven.

## Environment

- `WIKI_HOME`
  Override the global wiki home. Default: `~/.local/share/oh-my-superpowers/wiki`.
