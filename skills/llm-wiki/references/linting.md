# Linting

`omp wiki lint` is the wiki health check.

## When To Run

- After a synthesis pass (see `references/compile.md`).
- The wiki has grown after several ingest/synthesis cycles.
- Answers appear unstable or contradictory.
- Links may be stale.
- You suspect orphaned or low-quality compiled pages.

## V1 Behavior

Lint is report-only in v1.

It surfaces issues such as:

- broken wikilinks between wiki pages;
- missing index sections;
- obvious structural drift.

Wikilinks pointing into `raw/` (any depth of `../`, e.g. `../raw/foo.md` or
`../../raw/foo.md`) are treated as valid when the raw file exists. Lint reports
them as `missing raw target: …` only when the referenced raw file is gone.

Do not claim the wiki is healthy if lint reports unresolved issues.
