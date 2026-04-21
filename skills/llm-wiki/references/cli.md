# CLI Reference

Use `omp wiki` as the single entrypoint. The CLI is a thin **data plane**; it does not generate content.

## Commands

- `omp wiki init [--path <dir>]`
  Initialize the wiki home (`raw/`, `wiki/`, `state.json`).
- `omp wiki ingest <url-or-file> [--path <dir>]`
  Ingest a URL or local file into `raw/`.
- `omp wiki ingest --text --title <title> [--path <dir>]`
  Read stdin into `raw/`.
- `omp wiki nav [--json] [--path <dir>]`
  Show wiki file counts and `pending_synthesis` (raw files without a `wiki/sources/` page).
- `omp wiki lint [--json] [--path <dir>]`
  Report structural issues in the compiled wiki (broken wikilinks, missing headings).

## Reading and writing wiki pages

The caller agent reads and writes `wiki/` files directly using its own tools
(for example the `Read`, `Write`, and `Edit` tools). There is no `omp wiki read`
or `omp wiki compile` command — synthesis is SOP-driven, not CLI-driven.

## Path resolution

`--path` sets the wiki home directory (parent of `raw/` and `wiki/`).

Priority order:
1. `--path <dir>` — explicit override
2. `WIKI_HOME` env var — environment override
3. `<git-root>/wiki` — auto-detected when inside a git repo (project mode)
4. `~/.local/share/oh-my-superpowers/wiki` — global fallback
