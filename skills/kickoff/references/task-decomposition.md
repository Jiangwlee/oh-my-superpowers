# Task Decomposition

Read this in Phase 3 (Task Breakdown) and at the start of each wave when writing JIT specs.

---

## JIT Spec Protocol

Specs are written **wave by wave**, not upfront. Each wave's specs reflect what prior waves actually learned.

| Stage | What is filled |
|---|---|
| **Phase 3 — Breakdown (skeleton only)** | `tasks.yaml` entries: `id / title / wave / depends_on / files_modified（estimate）/ est_loc / test_layer`. `spec: null`, no `tasks/task-NN.md` file. |
| **Phase 4 — JIT Spec (per wave)** | Copy `skills/kickoff/templates/task.md` to `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md`. Fill `Objective / Protocol / Acceptance Checklist`. Set `spec: tasks/task-NN.md` in `tasks.yaml`. |

**Hard rule** (enforced by the `omp kickoff task update` CLI): flipping `status: executing` is rejected when `spec` is null/empty. Write the JIT spec first.

Before writing each wave's specs:

1. Read `story-memory.md` (mandated at the start of every wave).
2. Re-read prior wave's reviewer reports in case any deferred decision affects this wave's contract.
3. Then write the spec.

---

## tasks.yaml skeleton fields

Every entry MUST set: `id`, `title`, `wave`, `depends_on`, `spec` (null at breakdown), `files_modified`, `est_loc`, `test_layer`.

`test_layer` = the lowest layer that can falsify acceptance (Rule 1).
`est_loc` = estimated lines-of-code delta. Used by Phase 3 to pack tasks into ≤500-LOC waves.

- **Direct-edit fields**: appending, reordering, or removing tasks is a direct `tasks.yaml` edit. The `omp kickoff task` command handles only high-frequency state fields (status / worker / reviewer / commit / note / wave snapshot).
- **Sizing**: one task = one vertical slice. If a task touches more than 5 files, split **vertically** (two smaller features), not **horizontally** (all stores, then all components). See Rule 3.
- **Wave packing**: after the task list is dependency-ordered, pack adjacent independent tasks into the same wave while cumulative `est_loc` stays ≤ 500. The moment cumulative LOC would exceed 500, open a new wave. A single task whose `est_loc > 500` occupies its own wave (do NOT subdivide a vertical slice just to fit the budget).

---

## Rule 1: Test Layer Match

**The first red test in a task MUST be at the highest layer the acceptance criteria touch.**

| Acceptance describes | Required first-red-test layer |
|----------------------|-------------------------------|
| pure function input/output | unit |
| React hook state transitions | hook test |
| component rendering / interaction | component test |
| user observes URL/store/UI synchronized across navigation, mount, async | integration |
| browser-only behavior (lifecycle, focus, scroll, animation) | E2E |

**Default: E2E first.** Set `test_layer: e2e` unless acceptance is a pure data transform E2E cannot reach. E2E is the only layer the user actually observes — it is the real DoD.

Lower-layer tests are worker (or inline editor) discretion based on context.

---

## Rule 2: Cross-Layer API Wiring (No Orphans)

**Adding a shared API and wiring its consumer must happen in the same task.**

A "shared API" = any function/state/event that crosses module boundaries — store action, hook return value, context provider, event emitter, etc.

### Hard rules

1. **Forbidden**: task A "add `setDraftInput(id, text)` to store"; task B "wire ChatInput to use it".
2. **Required**: task "add cross-entity draft persistence" — touches store + ChatInput + integration test, all in one.
3. **Exception**: if API has 2+ consumers, task may add API + first consumer + integration test; subsequent consumers are separate tasks but each is its own vertical slice.

### Audit before finalizing breakdown

Scan the proposed task list. If any task description matches `add X to <module>` without a co-task `consume X in <component>` in the same task → **merge them**.

---

## Rule 3: Vertical Slice Sizing

One task = one vertical slice. A slice spans:

- model / store / state layer
- API / hook / transport layer
- component / view layer
- test (matching acceptance layer per Rule 1)

If a task touches more than 5 files, split — but **vertically** (two smaller features), not **horizontally** (all stores, then all components). Horizontal splits violate Rule 2.

---

## Self-check before dispatching a wave

- [ ] Does each task's first red test match its acceptance layer? (Rule 1)
- [ ] Any "add API" tasks without a paired "consume API" in the same task? (Rule 2)
- [ ] Is each task a vertical slice ≤ 5 files? (Rule 3)
- [ ] Cumulative `est_loc` of the wave's tasks ≤ 500 (or single task >500 occupies its own wave)?
- [ ] Has `story-memory.md` been read for the latest gotchas?

If any answer is "no", revise before dispatching.
