# Story Memory Guideline

Per-story explicit learning log. Read this when creating, appending to, or closing a `story-memory.md`.

---

## Purpose

`story-memory.md` captures **cross-task, story-scoped discoveries** so the next task's spec is informed by prior waves' lessons and reviewers do not re-flag already-resolved issues. Context compaction erases supervisor memory; without this file, every cross-task learning is re-derived or lost.

## Location

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

Created as an empty placeholder during story intake; filled in as the story progresses.

## Write Authority

- **Supervisor is the sole writer.** Workers and reviewers read only.
- In **inline mode**, supervisor distills its own task experience after each task.
- In **multi_wave mode**, workers surface candidates via completion report (`### Deviations`, `### Issues Found`, `### Story-Memory Impact`); supervisor decides what to promote.
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
| **Creation** | `omp coding-supervisor story init` writes an empty placeholder (title + three empty section headers). Full CLI usage: SKILL.md Phase 1 step 2. |
| **Accumulation** | After each task, supervisor paraphrases cross-task reusable findings and appends to the matching section. Raw copy-paste is forbidden. |
| **Consumption** | Phase 2 step 1 mandates reading this file BEFORE writing the next wave's JIT spec. In multi_wave mode the dispatch prompt also injects this file's contents for the worker. |
| **Promotion at close** | Phase 3 Self-Evaluation re-reads each entry: cross-story reusable → promote (`CLAUDE.md` for code-local rules, `insight` memory for project-global principles). Only this-story relevant → leave in place; archived with the story. |

Nothing is promoted silently; every promotion is an explicit supervisor action.

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
| `story.md` | Story narrative (what/how) | Supervisor (from design doc; immutable after intake) |
| `tasks.yaml` | Task state (SSOT) | Supervisor + workers (via `task.py`) |
| `tasks/task-NN.md` | Per-task spec (Objective / Protocol / Acceptance) | Supervisor (JIT, wave by wave) |
| `story-memory.md` | Cross-task learning digest | Supervisor (curated append only) |
| `story-summary.md` | Phase 3 self-evaluation report | Supervisor (once, at story close) |

Different scopes, different writers — do not blur them.
