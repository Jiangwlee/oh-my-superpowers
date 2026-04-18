# Task Spec Template

Orchestrator reads this file when breaking down a story into tasks.
Copy and fill for each task. Save as `./stories/<story-name>/tasks/task-NN.md`.

---

```markdown
---
task: NN
story: <story-name>
status: pending          # pending | executing | reviewing | testing | completed | blocked
wave: N                  # Orchestrator assigns: tasks with same wave can run in parallel
depends_on: []           # Task IDs this task requires (e.g., ["01", "03"])
files_modified: []       # Files this task will modify (for conflict detection)
test_layer: integration  # unit | hook | component | integration | e2e
                         # MUST match the highest layer the acceptance criteria touch.
                         # See references/task-decomposition-rules.md Rule 1.
                         # Lower-layer tests may be added as supplemental, but the
                         # acceptance-matching layer is the FIRST red test.
---

# Task: <action-oriented name>

## Context

<!-- WHY this task exists. Link to story and design docs. -->
<!-- Keep it short — sub agent reads the linked docs for detail. -->

Story: `./stories/<story-name>/story.md`
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
     These are behavioral protocols — the orchestrator passes paths,
     sub agent reads them. constitution.md is always included. -->

- `references/constitution.md` — coding principles (always include)
- `worker-refs/worker-guideline.md` — worker behavioral protocol (always include)
- `worker-refs/debugging-guideline.md` — include only if task has complex test plan

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
     The FIRST red test must be at the layer declared in `test_layer:` frontmatter.
     If acceptance describes user-observable behavior across navigation/mount/async,
     the first test is integration (real Provider tree, mocked router only) — NOT
     a hook unit test that will pass while the feature breaks in browser.
     See references/task-decomposition-rules.md Rule 1. -->

- [ ] <first red test at acceptance layer> — verifies <observable behavior>
- [ ] <supplemental lower-layer tests if useful> — verifies <internal contract>
- [ ] <E2E / browser verification — owned by THIS task, not a separate one> — see Rule 4

## Progress

<!-- Updated by orchestrator as pipeline advances. -->

- [ ] Execute — worker assigned: <runtime/agent-id or pending>
- [ ] Review — reviewer: <runtime or pending>
- [ ] Test — result: <pass/fail or pending>
- [ ] Acceptance — verified: <date or pending>
```

---

## Template Usage Notes

**Sizing**: one task = one vertical slice (model + API + UI for one feature). Prefer vertical over horizontal (all models, then all APIs). See `references/task-decomposition-rules.md` Rule 5 for the ≤5 files / vertical-only split rule.

**Cross-layer wiring**: if a task adds a shared API (store action, hook return, context value), the SAME task must wire its first consumer + ship an integration test. Splitting "add API" from "use API" produces orphaned APIs — see Rule 2.

**Test layer**: the `test_layer:` frontmatter field declares the layer for the first red test. It MUST match the highest layer the acceptance criteria touch — see Rule 1.

**Fix batching**: surgical fix tasks (≤30 lines each, ≤3 fixes, sharing a single verification cycle) MAY be combined into one fix-batch task instead of running full ceremony per fix. See Rule 3.

**Verification ownership**: the implementation task OWNS its E2E verification. Do not spawn a separate "verify story" task. See Rule 4.

**Read First vs References**: Read First = mandatory pre-reading before any code change. References = optional additional context.

**Must-Haves vs Test Plan**: Must-Haves define the goal (what must be true). Test Plan defines the method (how to verify). A task can pass all tests but fail must-haves if tests don't cover the actual goal.

**Deviation Rules customization**: the four levels above are defaults. Orchestrator should adjust per task — a security-critical task may move "adding dependencies" from 🔴 to absolute prohibition.

**Wave assignment**: Orchestrator assigns wave numbers. Same wave = can run in parallel (no file conflicts, no dependencies). Higher wave = depends on lower waves completing first.
