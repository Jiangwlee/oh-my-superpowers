---
name: coding-orchestrator
description: >-
  Use when coordinating multi-agent coding work on a feature, refactor, or bug
  that requires multiple tasks dispatched to sub-agents in sequential waves —
  even if the user doesn't say "orchestrate." Typical signals: "break this into
  tasks for different agents", "work in parallel", "manage a complex multi-file
  project end-to-end", or any request implying spec → dispatch → review → test
  cycles across multiple sub-agents.
  Do NOT trigger for tasks spanning ≤ 1 wave or ≤ 5 files — recommend direct
  coding with the main agent instead. Do NOT trigger if the user is still in
  the design/brainstorming phase — use the brainstorming skill first.
---

# Coding Orchestrator: Spec-Driven Sub-Agent Orchestration

<HARD-GATE>
The orchestrator does NOT write code. All coding, design, testing, and
debugging is delegated to sub-agents. If you catch yourself writing
implementation code, STOP — you are violating the orchestrator contract.
</HARD-GATE>

## Pipeline

**Before starting**: read `references/constitution.md` — Karpathy's four principles, applies to all roles including the orchestrator.

### Phase 1 — Story Initialization

1. **Story Intake** — Initialize a story. Details: `references/story-intake.md`.
2. **Task Breakdown** — Decompose into task skeleton; wave ≥ 2 leave `spec: null`. Protocol: `references/task-decomposition-rules.md`.

### Phase 2 — Wave Execution (loop until all tasks `status: completed`)

1. **Write JIT Spec** — for this wave, before dispatching. Read `references/task-decomposition-rules.md` before writing any spec.
2. **Execute** — dispatch coding tasks. Route/prompt protocol: `references/dispatch-routes.md`.
3. **Review** — dispatch code review + orchestrator second judgment. Protocol: `references/dispatch-routes.md` § Review Protocol.
4. **Test & Debug** — run tests; on failure see `references/dispatch-routes.md` § Test & Debug.
5. **Accept Task** — verify must_haves; mark passing tasks `completed`. Protocol: `references/acceptance.md`.
6. **Feedback & Revise** — capture reusable feedback into `story-memory.md`. Protocol: `references/story-memory-guideline.md`.
7. **Advance Wave** — when all current-wave tasks are `completed`, flip each next-wave task to executing:
   `omp coding-orchestrator task update --story <slug> --id <NN> --status executing`
8. **Report & Repeat** — report wave status in this format, then loop back to step 1:
   ```
   Wave N: X/Y completed — task-NN [status], task-MM [status]
   Next: <one-sentence next action>
   ```

### Phase 3 — E2E Testing & Acceptance

1. **E2E Test** — run E2E tests defined in task specs.
2. **Debug & Fix** — on failure see `references/dispatch-routes.md` § Test & Debug.
3. **Rerun E2E** — repeat until passing.
4. **Acceptance** — verify must_haves per task spec. Protocol: `references/acceptance.md`.

## Compaction Recovery

Read `<PROJECT_ROOT>/stories/.handoff-context`. Details: `references/handoff-guideline.md`.

## Storage

`stories/` lives at `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/`. Details: `references/storage-layout.md`.
