# Story Memory Guideline

Per-story explicit learning log. Read this when creating, appending to, or closing a `story-memory.md`.

---

## Purpose

`story-memory.md` captures **cross-task, story-scoped discoveries** so the next task's spec is informed by prior waves' lessons and reviewers do not re-flag already-resolved issues. Context compaction (which the user performs between waves) erases your memory; without this file, every cross-task learning is re-derived or lost.

## Location

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

Created as an empty placeholder during story init; filled in as the story progresses.

## Write Authority

- **You (kickoff) are the sole writer.** Sub-agents and reviewers read only.
- After each task you complete inline, distill the cross-task reusable lessons.
- For sub-agent tasks, the sub-agent surfaces candidates via its completion report's `deviations`, `next-task-hint`, and `story-memory-impact` lines (see `references/execution.md` for the full report contract); you decide what to promote.
- Single-writer curation is what keeps the file a **digest**, not a log.

## Structure

Three sections, added as needed. Omit a section if nothing to record yet.

```markdown
# Story Memory: <slug>

## Patterns
- <cross-task reusable discovery>; seen in: task-NN, task-MM

## Gotchas
- <subtle trap, with enough context that the next task avoids it>

## Known False Positives (for reviewers)
- <check that looks wrong but is intentional, with link to the deciding task>
```

Each bullet must include:

- **What** — the observation, specific enough to match in a different task.
- **Where / Why** — the task(s) that established it, or the rationale.
- **(optional) pointer** — a commit, PR comment, or discussion if relevant.

Do not paste raw worker reports, dated quotes, or unstructured dumps.

## Lifecycle

| Stage | Action |
|---|---|
| **Creation** | `omp kickoff story init` writes an empty placeholder (title + three empty section headers). |
| **Accumulation** | After each task, paraphrase cross-task reusable findings and append to the matching section. Raw copy-paste is forbidden. |
| **Consumption** | At the start of each wave you MUST read this file BEFORE writing the next wave's JIT specs. When dispatching a sub-agent worker, inject this file's contents into the dispatch prompt. |
| **Promotion at close** | Phase 5 Self-Evaluation re-reads each entry: cross-story reusable → promote (`CLAUDE.md` for code-local rules, `insight` memory for project-global principles). Only this-story relevant → leave in place; archived with the story. |

Nothing is promoted silently; every promotion is an explicit kickoff action.

## Anti-patterns

| ❌ Don't | Why |
|---|---|
| Paste worker reports verbatim | Story-memory is a digest; raw history lives in git log and per-task spec |
| Write entries that apply across all stories | Those belong in `CLAUDE.md` or `insight` memory |
| Let workers edit directly | Multi-writer → drift + duplicates |
| Grep archived stories for cross-story reuse | Once archived, story-memory is frozen; reuse must happen via the promotion step |

## Relationship to other files

| File | Role | Writer |
|---|---|---|
| `story.md` | Story narrative (what/how) | You (from user requirement; immutable after Phase 1) |
| `tasks.yaml` | Task state + wave snapshots (SSOT) | You + sub-agents (via `omp kickoff task` CLI) |
| `tasks/task-NN.md` | Per-task spec (Objective / Protocol / Acceptance) | You (JIT, wave by wave) |
| `story-memory.md` | Cross-task learning digest | You (curated append only) |
| `story-summary.md` | Phase 5 self-evaluation report | You (once, at story close) |

Different scopes, different writers — do not blur them.
