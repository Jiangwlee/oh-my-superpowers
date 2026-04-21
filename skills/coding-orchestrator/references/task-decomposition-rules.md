# Task Decomposition Rules

Read this when breaking a story into tasks and when writing JIT specs wave by wave.

---

## JIT Spec Writing Protocol

Task specs are written **wave by wave**, not upfront. Each wave's specs reflect what prior waves actually learned.

Orchestrator writes every spec. Both entry paths share the same JIT rule:

| Entry path | Wave 1 spec source | Wave ≥ 2 |
|---|---|---|
| **A (handoff)** | Brainstorming design doc | `spec: null` until prior wave completes |
| **B (self-created)** | User's direct request | `spec: null` until prior wave completes |

Wave ≥ 2 specs are written JIT once prior waves complete, informed by their worker reports and the current `story-memory.md`.

## Phase 1 Skeleton Review Gate

Before wave 1 dispatch, run the `task-skeleton-reviewer` agent (see SKILL.md Agents table).

- Route this review to an L3 reviewer.
- The reviewer returns JSON with `merge`, `split`, `rewave`.
- Orchestrator applies or explicitly rejects each proposed change before dispatching wave 1.
- Brainstorming may suggest better slicing, but this gate is the enforcement point.

**Hard rule — enforced by `scripts/task.py`**: flipping `status: executing` is rejected (exit 2) whenever the target task's `spec` is null, missing, or empty. Write the spec first.

Before dispatching each wave:

1. Read every completed prior-wave Worker Report (esp. `### Story-Memory Impact`, `### Deviations`, `### Issues Found`) and the current `story-memory.md`.
2. Decide what to promote into `story-memory.md` (see `references/story-memory-guideline.md` — paraphrase, never paste raw).
3. Copy `templates/task.md` to `tasks/task-NN.md` for every task in the upcoming wave. Fill `Objective`, `Read First`, `File Scope`, `Deviation Rules`, `Must-Haves`, `Test Plan`. `Worker Refs` is pre-populated to include `../story-memory.md`.
4. Set `spec: tasks/task-NN.md` on each task's `tasks.yaml` entry.
5. Flip status to `executing`.

### tasks.yaml skeleton

Every entry must set: `id`, `title`, `wave`, `depends_on`, `spec`, `files_modified`, `test_layer`. `test_layer` = the lowest layer that can falsify acceptance (Rule 1).

- **Direct-edit fields**: appending, reordering, or removing tasks is a direct `tasks.yaml` edit. The `omp` command handles only high-frequency fields (status / worker / reviewer / commit / note).
- **Sizing**: one task = one vertical slice. If a task touches more than 5 files, split it **vertically** (two smaller features), not **horizontally** (all stores, then all components). See Rule 5.
- **Self-check**: before dispatching each wave, run the checklist at the bottom of this file. Revise if any answer is "no".

---

## Rules

Rules 1–3 address three recurring orchestrator mistakes:

| Mistake | Symptom |
|---|---|
| **Test layer mismatch** | Spec says "TDD red test first"; worker writes a hook unit test; acceptance is integration-level. Tests pass but feature fails E2E. |
| **Cross-layer wiring split** | "Add store API" and "wire it into component" land in separate tasks. API ships orphaned; bug surfaces rounds later. |
| **Surgical-fix overhead inflation** | Every 5-line bug fix runs the full task ceremony. 70%+ of task time is overhead, not fixing. |

Rules 4 and 5 address verification ownership and vertical sizing.

---

## Rule 1: Test Layer Match

**The first red test in a task MUST be at the highest layer the acceptance criteria touch.**

### Acceptance → required test layer

| Acceptance describes | Required first-red-test layer |
|----------------------|-------------------------------|
| pure function input/output | unit |
| React hook state transitions | hook test (e.g., `renderHook`) |
| component rendering / interaction | component test (e.g., `@testing-library/react`) |
| **user observes URL/store/UI synchronized across navigation, mount, async** | **integration test (real Provider tree, mocked router only)** |
| browser-only behavior (lifecycle, focus, scroll, animation) | E2E (Playwright / chrome-devtools MCP) |

**Hard rule**: orchestrator may not write a task spec whose first red test is at a *lower* layer than the acceptance demands. Lower-layer tests may be added as supplemental, but the acceptance-matching layer comes first.

### Anti-pattern (real example)

❌ Acceptance: "切换 /agents/a → /agents/b 后，store.draftInputs 仍存在"
   First test: `useChatStore` hook unit test → passes ✅, but real Provider mount race makes feature fail in browser.

✅ Acceptance: same.
   First test: integration — mount real `<ChatProvider>` + mock `useRouter`, dispatch `router.push`, assert store.draftInputs persists.

### How to enforce

When writing a task spec, read the **acceptance criteria first**, then ask: "what's the lowest test layer that can falsify this criterion?" That is the required first-red-test layer. Set it as the `test_layer` field of the task's entry in `tasks.yaml` (see `templates/tasks.yaml`).

---

## Rule 2: Cross-Layer API Wiring

**Adding a shared API and wiring its consumer must happen in the same task.**

A "shared API" means: any function/state/event that crosses module boundaries — store action, hook return value, context provider, event emitter, etc.

### Why

When split:
- task-N adds the API; tests prove the API works in isolation
- task-N+1 (or later) wires the consumer; might never happen, or happens with a different mental model
- ORPHAN APIs accumulate; bugs surface in E2E rounds

When merged:
- single task delivers a vertical slice (API + consumer + integration test)
- acceptance test naturally covers the wiring
- impossible to ship orphaned APIs

### Hard rules

1. **Forbidden**: task A "add `setDraftInput(id, text)` to store"; task B "wire ChatInput to use it"
2. **Required**: task "add cross-entity draft persistence" — touches store + ChatInput + integration test, all in one
3. **Exception**: if API has 2+ consumers, the task may add API + first consumer + integration test; subsequent consumers are separate tasks but each is its own vertical slice (consumer + its own integration test)

### Audit trigger

Before finalizing task breakdown, scan the proposed task list. If any task description matches the pattern `add X to <module>` without a co-task `consume X in <component>` in the same task, **merge them**.

---

## Rule 3: Surgical Fix Batching

**Fixes under 30 changed lines may be batched into one task, up to 3 fixes per batch, when they share a common verification cycle.**

### Trigger

Applies to fix-loop tasks born from acceptance failures. Does NOT apply to feature implementation.

### Conditions (all must hold)

1. Each fix changes ≤ 30 lines
2. All fixes are validated by the same test command or browser session
3. Fixes don't interact (one fix doesn't depend on another being merged first)
4. Total batch ≤ 3 fixes

### How

Write one task spec covering all fixes:
- Title: "fix-batch: X / Y / Z"
- Each fix gets its own subsection under Objective with its own Read First / File Scope
- Single Acceptance section listing all expected outcomes
- One verification cycle at the end

### Anti-pattern

❌ task-15: fix race in hook (5 lines) → full task ceremony
   task-17: fix idempotent select (8 lines) → full task ceremony
   task-19: fix safeDecode (12 lines) → full task ceremony
   Total overhead: 3× spec + 3× dispatch + 3× review + 3× handoff

✅ task-15: fix-batch (race + idempotent + safeDecode), 25 lines total
   Total overhead: 1× spec + 1× dispatch + 1× review + 1× handoff

### Forbidden

- Batching fixes that touch the same file in conflicting ways
- Batching > 3 fixes (split into 2 batches)
- Batching feature work with fixes (mixed scope)

---

## Rule 4: Verification Tasks Are Not Tasks

**E2E acceptance verification belongs to the implementation task, not a separate task.**

### Why

A separate "run E2E and report" task creates a ping-pong loop:
- task-N implements → task-N+1 verifies ❌ → task-N+2 fixes one bug → task-N+3 verifies ❌ → ...

Each verification cycle adds ceremony but contributes zero implementation. Bugs found this way should be fixed inside the original task's loop, not spawned as new tasks.

### Hard rules

1. **Implementation task owns verification**: every implementation task spec must include `## Test Plan` with E2E commands + browser steps. The same worker runs them.
2. **Acceptance failure → fix in same task**: if E2E fails inside the task, the worker iterates within the task's iteration limit (default 3 attempts). Failure beyond limit escalates per `references/handoff-guideline.md`.
3. **No standalone "verify story" tasks**: a story is verified by the union of its task acceptances. If you feel the urge to write task-N "run all b1-b11 cases", you've under-specified the per-task acceptances.

### Exception

Story-level merge readiness check (handoff doc + final test counts) MAY be a separate small task — but it should not run E2E cases, only aggregate evidence already produced by implementation tasks.

---

## Rule 5: Vertical Slice Sizing

One task = one vertical slice. A slice spans:

- model / store / state layer
- API / hook / transport layer
- component / view layer
- test (matching acceptance layer per Rule 1)

If a task touches more than 5 files, split — but **vertically** (two smaller features), not **horizontally** (all stores, then all components). Horizontal splits violate Rule 2.

---

## Self-check before finalizing task breakdown

- [ ] Does each task's first red test match its acceptance layer? (Rule 1)
- [ ] Any "add API" tasks without a paired "consume API" in the same task? (Rule 2)
- [ ] If this is a fix loop, are batchable fixes batched? (Rule 3)
- [ ] Any standalone verification tasks that could fold into implementation? (Rule 4)
- [ ] Is each task a vertical slice ≤ 5 files? (Rule 5)
- [ ] Did the skeleton review gate run, and is every merge / split / rewave suggestion resolved?

If any answer is "no" or "I don't know", revise before dispatching.
