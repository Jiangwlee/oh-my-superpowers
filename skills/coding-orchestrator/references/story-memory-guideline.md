# Story Memory Guideline

Per-story explicit learning log. Orthogonal to `.handoff-context` (state checkpoint). Read this when creating, appending to, or closing a `story-memory.md`.

---

## Purpose

`story-memory.md` captures **cross-task, story-scoped discoveries** so workers start pre-aware of gotchas and reviewers do not re-flag already-resolved issues. Context compaction erases orchestrator memory; without this file, every cross-task learning is re-derived or lost.

## Location

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

Created as an empty placeholder during story intake; filled in as the story progresses.

## Write Authority

- **Orchestrator is the sole writer.** Workers and reviewers read only.
- Workers surface candidate entries via their completion report (`### Deviations`, `### Issues Found`, `### Story-Memory Impact`). The orchestrator decides what to promote.
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
| **Creation** | Orchestrator writes an empty placeholder during story intake (title + three empty section headers). |
| **Accumulation** | After each wave, orchestrator reads worker reports (esp. `Story-Memory Impact`), **paraphrases** what is cross-task reusable, and appends to the matching section. Raw copy-paste is forbidden. |
| **Consumption** | Every task spec's Worker Refs lists `../story-memory.md` by default. Workers read it before designing; reviewers read it before flagging issues. |
| **Promotion at close** | Orchestrator re-reads each entry and asks: cross-story reusable → promote (`CLAUDE.md` for code-local rules, `insight` memory for project-global principles). Only this-story relevant → leave in place; archived with the story. |

Nothing is promoted silently; every promotion is an explicit orchestrator action.

## Anti-patterns

| ❌ Don't | Why |
|---|---|
| Paste worker reports verbatim | Story-memory is a digest; raw history lives in `.handoff-context` and git log |
| Write entries that apply across all stories | Those belong in `CLAUDE.md` or `insight` memory |
| Let workers edit directly | Multi-writer → drift + duplicates |
| Grep archived stories for cross-story reuse | Once archived, story-memory is frozen; reuse must happen via the promotion step |

## Relationship to other files

| File | Role | Writer |
|---|---|---|
| `story.md` | Story narrative (what/how) | Orchestrator (from design doc; immutable after intake) |
| `tasks.yaml` | Task state (SSOT) | Orchestrator + workers (via `task.py`) |
| `tasks/task-NN.md` | Per-task spec | Orchestrator (JIT, wave by wave) |
| `.handoff-context` | Task-level recovery checkpoint | Orchestrator (`handoff update`) |
| `story-memory.md` | Cross-task learning digest | Orchestrator (curated append only) |

Different scopes, different writers — do not blur them.
