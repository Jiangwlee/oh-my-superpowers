# Story Memory Guideline

Per-story explicit learning log. Orthogonal to `handoff.md` (state snapshot).
Read this when creating, appending to, or closing a `story-memory.md`.

---

## Purpose

`story-memory.md` captures **cross-task, story-scoped discoveries** so that:

- Workers dispatched to later tasks start pre-aware of the story's gotchas
- Reviewers avoid re-flagging issues the team already debated and resolved
- Patterns that emerge during execution are explicit, not trapped in the orchestrator's ephemeral context

It exists because context compaction erases orchestrator memory; without an explicit file, every cross-task learning is re-derived or lost.

## Location

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

Created as an empty placeholder by **brainstorming** at the end of the S3 scenario; filled in by **coding-orchestrator** as the story progresses.

## Write Authority

- **coding-orchestrator is the sole writer.** Workers and reviewers read only.
- Workers surface candidate entries via their completion report (`### Deviations`, `### Issues Found`, `### Story-Memory Impact`). The orchestrator evaluates those candidates and decides what to promote into `story-memory.md`.
- Writing through a single author is what keeps the file dense and curated — it is a **digest**, not a log.

## Structure

Three sections, added as needed. Omit a section if there is nothing to record yet.

```markdown
# Story Memory: <slug>

## Patterns
- <cross-task reusable discovery>; seen in: task-NN, task-MM

## Gotchas
- <subtle trap, with enough context that next task avoids it>

## Known False Positives (for reviewers)
- <check that looks wrong but is intentional, with link to the task that decided it>
```

Each bullet must include:
- **What** — the observation, specific enough to match in a different task
- **Where / Why** — the task(s) that established it, or the rationale
- **(optional) pointer** — to a commit, PR comment, or discussion if relevant

Avoid: dated raw quotes, worker reports pasted in full, unstructured dumps.

## Lifecycle

1. **Creation** — brainstorming writes an empty placeholder at end of S3 (title + three empty section headers).
2. **Accumulation** — after each wave completes, orchestrator reads worker reports (esp. `Story-Memory Impact` line), decides what is cross-task reusable, **paraphrases** it, and appends to the matching section. Raw copy-paste is forbidden.
3. **Consumption** — every task spec's Worker Refs section lists `../story-memory.md` by default; workers read it before designing. Reviewers also read it before flagging issues.
4. **Promotion at close** — when the story finishes, orchestrator re-reads `story-memory.md` and asks for each entry:
   - **Cross-story reusable?** Promote to a nearby `CLAUDE.md` (for code-local rules) or to `insight` memory (for project-global principles).
   - **Only this-story relevant?** Keep in place; story-memory.md is archived with the story directory.

Nothing is promoted silently; every promotion is an explicit orchestrator action.

## Anti-patterns

- ❌ **Raw log**: appending worker reports verbatim. Story-memory is a **digest**; if a reader needs raw history, they read handoff.md or git log.
- ❌ **Global memory in disguise**: writing entries that apply across all stories. Those belong in `CLAUDE.md` or `insight` memory, not in a per-story file.
- ❌ **Worker self-append**: letting workers edit story-memory.md directly. Multiple writers without curation = drift + duplicates.
- ❌ **Reading after archive**: once a story is archived, story-memory.md is frozen history. Cross-story reuse must happen via the promotion step before archive, not via grep over archived stories.

## Relationship to other files

| File | Role | Writer |
|---|---|---|
| `story.md` | Story narrative (what/how) | brainstorming (immutable after handoff) |
| `tasks.yaml` | Task state (SSOT) | coding-orchestrator + workers (via task.py) |
| `tasks/task-NN.md` | Per-task spec | coding-orchestrator (JIT, wave by wave) |
| `handoff.md` | Compaction-survival snapshot | PreCompact hook (auto) |
| `story-memory.md` | Cross-task learning digest | coding-orchestrator (curated append only) |

Each has a different scope and writer; do not blur them.
