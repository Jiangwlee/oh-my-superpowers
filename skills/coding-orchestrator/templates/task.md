# Task Spec Template

Worker-prompt template. This file is **narrative only** — state lives in `tasks.yaml`.
Copy and fill for each task. Save as `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md`.

Structured fields (`status`, `wave`, `depends_on`, `files_modified`, `test_layer`,
`worker`, `reviewer`, `commits`, timestamps) are managed in `tasks.yaml` via
`omp coding-orchestrator task update`. Do NOT duplicate them here.

---

```markdown
# Task: <action-oriented name>

## Context

<!-- WHY this task exists. Link to story and design docs. -->
<!-- Keep it short — sub agent reads the linked docs for detail. -->

Story: `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story.md`
Design: `<link to brainstorming design doc if applicable>`

<one paragraph explaining the motivation>

## Objective

<!-- WHAT to do and what NOT to do. Be specific. -->

**Do:**
- <concrete deliverable 1>
- <concrete deliverable 2>

**Do NOT:**
- <explicit exclusion>

## Read First

<!-- Files the sub agent MUST read before modifying anything. -->
<!-- Prevents blind changes. Be precise — file + line range when possible. -->

- `src/path/to/main-file.ts` — understand current implementation
- `src/path/to/types.ts:1-30` — existing type definitions
- `tests/path/to/existing.test.ts` — current test patterns

## File Scope

<!-- ONLY these files may be modified. Anything else requires escalation. -->

- `src/path/to/main-file.ts` — primary change target
- `src/path/to/types.ts` — may need new types
- `tests/path/to/test-file.test.ts` — test file

## Workflow

<!-- Guide the sub agent's explore → design → code flow. -->
<!-- Not prescriptive HOW, but WHAT to investigate and in what order. -->

1. Read files in Read First to understand current state
2. <design step — data structures, interfaces>
3. <implementation step — what to build>
4. <test step — what to verify>

## Worker Refs

<!-- Files the sub agent MUST read at the start of execution.
     Mode-dependent:
     - Mode=multi_wave: worker sub-agent reads all listed files before coding.
       Orchestrator pre-populates `../story-memory.md`; add the others as below.
     - Mode=inline: no worker sub-agent exists. Orchestrator reads story-memory.md
       itself; the rest of this section may be omitted. Delete this section or
       mark it N/A when the task's story is Mode=inline. -->

- `references/constitution.md` — coding principles (always include, multi_wave)
- `worker-refs/worker-guideline.md` — worker behavioral protocol (always include, multi_wave)
- `../story-memory.md` — this story's accumulated patterns / gotchas / known false positives (both modes)
- `worker-refs/debugging-guideline.md` — include only if task has complex test plan (multi_wave)

## References

<!-- Additional files, docs, or URLs the sub agent may need. -->
<!-- NOT the same as Read First — these are optional context. -->

- `docs/design/xxx.md` — related design decisions
- `src/path/to/similar-feature.ts` — reference implementation

## Deviation Rules

<!-- Four-level autonomy control. Sub agent follows these without asking
     for levels 🟢🟡🟠, and MUST ask for 🔴. -->

🟢 **Auto-fix** (just do it, track in progress):
- Bug fixes that don't change interfaces
- Missing imports/exports
- Typo fixes in code (not comments)

🟡 **Auto-add** (do it, note the deviation):
- Critical missing error handling that would cause crashes
- Missing null/undefined checks on external input
- Test cases for edge cases discovered during implementation

🟠 **Auto-fix blocking** (do it, it's blocking progress):
- Dependency conflicts preventing compilation
- Type mismatches between modules
- Missing configuration that blocks execution

🔴 **Ask orchestrator** (STOP and report):
- Modifying public API signatures
- Adding new dependencies
- Touching files outside File Scope
- Architectural changes (new modules, changed data flow)

## IRON LAW

<!-- Reference coding guideline + task-specific hard constraints. -->

Follow `references/constitution.md`:
- Think Before Coding → Simplicity First → Surgical Changes → Goal-Driven

**Analysis paralysis guard**: 5+ consecutive reads without any edit/write = stuck.
When stuck:
1. Write down current understanding and confusion
2. Pick the smallest viable change and execute it
3. Still stuck → report to orchestrator with blocker reason

**Task-specific constraints:**
- <hard constraint specific to this task>

## Acceptance Criteria

### Must-Haves

<!-- Goal-backward verification. These define DONE, not the tasks above. -->

**Truths** (observable behaviors that must be true):
- "<user-facing behavior, e.g., User can log in with new password>"
- "<another behavior>"

**Artifacts** (files that must exist with real implementation):
- path: `src/path/to/file.ts`
  provides: "<what this file delivers>"
  contains: "<pattern that must exist, e.g., export function login>"

**Key Links** (critical connections between artifacts):
- from: `src/path/to/component.ts`
  to: `src/path/to/api.ts`
  pattern: `import.*from.*api`

## Test Plan

<!-- What to test and how. Sub agent executes these.
     Layer selection: see references/task-decomposition-rules.md Rule 1. -->

- [ ] <first red test at acceptance layer> — verifies <observable behavior>
- [ ] <supplemental lower-layer tests if useful> — verifies <internal contract>
- [ ] <E2E / browser verification — owned by THIS task, not a separate one> — see Rule 4
```

---

## Template Usage Notes

Cross-references live in `references/task-decomposition-rules.md`. Keep this section short.

| Topic | Rule |
|---|---|
| **Sizing** | One task = one vertical slice; ≤5 files; split vertically, not horizontally. See Rule 5. |
| **Cross-layer wiring** | A task that adds a shared API must also wire its first consumer and ship an integration test. See Rule 2. |
| **Test layer** | `test_layer` in `tasks.yaml` must match the highest layer the acceptance criteria touch. See Rule 1. |
| **Fix batching** | Fix-loop tasks may combine ≤3 fixes, ≤30 lines each, sharing one verification cycle. See Rule 3. |
| **Verification ownership** | The implementation task owns its E2E verification. Never spawn a separate "verify story" task. See Rule 4. |

Other distinctions:

- **Read First vs References** — Read First is mandatory pre-reading before any code change; References is optional context.
- **Must-Haves vs Test Plan** — Must-Haves define the goal; Test Plan defines the method. A task can pass every test and still fail acceptance if the test plan does not cover the goal.
- **Deviation Rules** — the four levels above are defaults. Orchestrator may tighten per task (e.g., promote "add dependency" from 🔴 to absolute prohibition for a security-critical task).
- **Wave assignment** — same wave = parallelizable (no file conflicts, no dependencies); higher wave = depends on lower waves completing first.
