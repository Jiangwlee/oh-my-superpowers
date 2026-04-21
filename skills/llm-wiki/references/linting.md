# Linting

`omp wiki lint` is the wiki health check. Two categories with different authority levels.

## Deterministic Checks (auto-fix)

Fix these automatically:

**Broken wikilinks** — for every `[[...]]` link in wiki/ files:
- Target does not exist → search wiki/ for a file with the same name elsewhere.
  - Exactly one match → fix the path.
  - Zero or multiple matches → report to user.

**Index consistency** — compare `wiki/index.md` against actual wiki/ files (excluding index.md and log.md):
- File exists but missing from index → add entry with `(no summary)` placeholder.
- Index entry points to nonexistent file → mark as `[MISSING]`. Do not delete; let user decide.

**Raw references** — every link in a `Raw:` metadata field must point to an existing raw/ file:
- Target does not exist → search raw/ for a file with the same name elsewhere.
  - Exactly one match → fix the path.
  - Zero or multiple matches → report to user.

## Heuristic Checks (report only)

Report findings without auto-fixing:

- Factual contradictions across concept pages
- Outdated claims superseded by newer sources
- Missing conflict annotations where sources disagree
- Orphan pages with no inbound links from other wiki articles
- Concepts frequently mentioned across sources but lacking a dedicated concept page
- Archive pages whose cited source articles have been substantially updated since archival

## Post-Lint

Append to `wiki/log.md`:

```
- YYYY-MM-DD  lint | N issues found, M auto-fixed
```

Do not claim the wiki is healthy if lint reports unresolved issues.
