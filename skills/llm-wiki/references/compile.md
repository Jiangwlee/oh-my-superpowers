# Compile SOP

The "compile" step is **caller-agent work**, not CLI work. The CLI's role stops at
reporting which raw files are uncovered (`omp wiki nav --json` → `pending_synthesis`).
This document is the playbook the agent follows to turn raw sources into wiki pages.

## Inputs

- `omp wiki nav --json` output, especially `pending_synthesis`.
- `raw/*.md` files already normalized by `omp wiki ingest`.
- Existing pages under `wiki/sources/`, `wiki/concepts/`, `wiki/maps/`, `wiki/index.md`.

## Output layout

```
wiki/
  index.md        # top-level navigation
  log.md          # append-only event log
  AGENTS.md       # schema (do not rewrite casually)
  sources/<slug>.md   # 1 per raw source
  concepts/<slug>.md  # cross-source concepts
  maps/<slug>.md      # reading paths / high-level maps
```

Slugs for `sources/*` should match the `raw/*.md` filename so `pending_synthesis`
coverage detection works by simple filename equality.

## Steps

### 1. Per-source summary — `wiki/sources/<slug>.md`

For each entry in `pending_synthesis`:

1. Read `raw/<slug>.md`.
2. Write `wiki/sources/<slug>.md` using `references/source-template.md`.
3. Keep the link back to raw: `[[../../raw/<slug>.md]]` — nav uses this as a coverage signal.
4. Distill; do not copy the raw body verbatim. Use blockquotes sparingly for original phrasing worth preserving.

### 2. Concepts — `wiki/concepts/<slug>.md`

A concept page is justified when a term or idea is discussed across **two or more** source pages.

1. Identify recurring terms across `wiki/sources/*.md`.
2. For each qualifying concept, create or update `wiki/concepts/<concept-slug>.md` using
   `references/concept-template.md`.
3. Cite the contributing source pages via wikilinks: `[[../sources/<slug>.md]]`.

Do not create a concept page for a term mentioned in a single source.

### 3. Maps — `wiki/maps/<slug>.md`

A map page is a reading path: "if you want to understand X, read A → B → C".
Create or update `wiki/maps/<slug>.md` when:

- There is a coherent narrative across several concepts/sources.
- A reader new to the topic would benefit from an ordered entry point.

Use `references/map-template.md`.

### 4. Cascade and contradictions

When a new source contradicts or refines an existing concept page:

1. Update the concept page in place — do not leave two conflicting claims.
2. Note the resolution in the "Contradictions / Open questions" section of the concept page.
3. If the old claim is still worth preserving, move it under a clearly labeled history heading rather than deleting silently.

### 5. Index and log

After writing/updating pages:

1. Update `wiki/index.md` so the new source/concept/map pages are reachable.
2. Append one line to `wiki/log.md`:

   ```
   - YYYY-MM-DD  synthesized N source(s), updated M concept(s), touched K map(s)
   ```

### 6. Verify

Run `omp wiki lint` — fix broken wikilinks before stopping. Then re-run `omp wiki nav --json`
and confirm `pending_synthesis` is now empty (or shorter, if you covered only a subset).

## Stop conditions

Stop synthesis when **any** of the following hold:

- `pending_synthesis` is empty.
- You have covered the specific raw files the user asked about.
- You detect that further synthesis requires judgment calls the user has not authorized
  (e.g., merging two conflicting concept pages without guidance).

Surface the stop reason explicitly; do not silently leave `pending_synthesis` non-empty.
