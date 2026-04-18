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

Wikilinks pointing to `../raw/<file>.md` are considered always valid as long as the
raw file exists — lint does not consider them broken even though they sit outside `wiki/`.

Do not claim the wiki is healthy if lint reports unresolved issues.
