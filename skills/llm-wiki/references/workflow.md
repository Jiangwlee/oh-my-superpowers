# Workflow

The Karpathy-style flow, split across CLI and caller agent:

1. **Ingest** new material into `raw/` — `omp wiki ingest …` (CLI).
2. **Synthesize** it into `wiki/` — caller agent writes markdown, following `references/compile.md` (SOP).
3. **Navigate** the wiki — `omp wiki nav` surfaces entrypoints and `pending_synthesis`.
4. **Answer** questions from compiled pages.
5. **Lint** — `omp wiki lint` when quality may have drifted.

## Query Path

1. `omp wiki nav` — get entrypoints, counts, and the list of raw files pending synthesis.
2. Read `wiki/index.md` (the caller agent uses its own `Read` tool on the path reported by nav).
3. Read relevant files under `wiki/sources/`, `wiki/concepts/`, and `wiki/maps/`.
4. Only consult `raw/` when compiled coverage is clearly insufficient — and in that case, run the compile SOP to close the gap.

## Synthesis Path (when `pending_synthesis` is non-empty)

1. Load `references/compile.md` for the full SOP.
2. For each raw file listed in `pending_synthesis`:
   - Read `raw/<name>.md`.
   - Write `wiki/sources/<name>.md` using `references/source-template.md`.
3. Extract cross-cutting concepts into `wiki/concepts/<concept>.md` (`references/concept-template.md`).
4. Update or create `wiki/maps/<map>.md` for reading paths (`references/map-template.md`).
5. Update `wiki/index.md`.
6. Append a one-line entry to `wiki/log.md`.
7. Run `omp wiki lint` and fix any broken wikilinks before stopping.

## Anti-Patterns

- Do not treat `raw/` as the default query layer.
- Do not skip synthesis when `pending_synthesis` is non-empty but proceed to deep answers.
- Do not fabricate coverage when the compiled wiki is sparse.
- Do not expect the CLI to generate summaries — the CLI only moves bytes; the caller agent writes prose.
