---
name: coding-orchestrator
description: >-
  Spec-driven coding orchestration with sub-agent dispatch.
  Trigger: user says "orchestrate", acts as orchestrator, or invokes
  via slash command. Breaks work into task specs, dispatches sub-agents
  for coding/review/testing, tracks progress across context compactions.
---

# Coding Orchestrator: Spec-Driven Sub-Agent Orchestration

<HARD-GATE>
The orchestrator does NOT write code. All coding, design, testing, and
debugging is delegated to sub agents. If you catch yourself writing
implementation code, STOP — you are violating the orchestrator contract.
</HARD-GATE>

## Pipeline

**Before starting**: read `references/constitution.md` — Karpathy's four principles, applies to all roles including the orchestrator.

Create a task for each step and complete them in order:

1. **Story Intake** — validate a brainstorming S3 skeleton or create one; both paths require `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/`. Details: `references/story-intake.md`.
2. **Task Breakdown** — decompose into tasks with JIT wave-by-wave spec writing. Read `templates/task.md` and `references/task-decomposition-rules.md` before writing any spec.
3. **Execute** — dispatch sub agents for coding (worktree isolation for parallel). Route/prompt protocol: `references/dispatch-routes.md`.
4. **Review** — dispatch sub agent for code review + orchestrator second judgment.
5. **Test & Debug** — on failure, sub agent reads `worker-refs/debugging-guideline.md` (already listed in the task spec's Worker Refs).
6. **Acceptance** — verify must_haves from each task spec.

## Task Breakdown

**Before writing any task spec, read `references/task-decomposition-rules.md`.** It encodes hard rules for test-layer match, cross-layer API wiring, surgical-fix batching, and verification-task folding — all derived from real story post-mortems where ignoring them cost 5-10 extra fix-loop tasks.

### JIT wave-by-wave spec writing

Task specs are written **wave by wave**, not all at once. Each wave's specs reflect what prior waves actually learned.

- **Path A (handoff)**: wave 1 specs arrive pre-written. Wave ≥ 2 enter with `spec: null` — you write them JIT before dispatching that wave.
- **Path B (self-created)**: you write the full skeleton, populating only wave-1 `spec` fields. Leave wave ≥ 2 as `spec: null`.

**Hard rule — enforced by `scripts/task.py`**:

> `omp coding-orchestrator task update --status executing` is rejected (exit 2) whenever the target task's `spec` is null, missing, or empty. Write the spec first, or the dispatch fails.

Before dispatching each wave:
1. Read every completed prior-wave task's Worker Report (esp. `### Story-Memory Impact`, `### Deviations`, `### Issues Found (out of scope)` — structure defined in `worker-refs/worker-guideline.md`) and the current `story-memory.md`.
2. Decide what to promote into `story-memory.md` (see `references/story-memory-guideline.md` — paraphrase, don't paste raw).
3. Copy `templates/task.md` to `tasks/task-NN.md` for each task in the upcoming wave. Fill `Objective`, `Read First`, `File Scope`, `Deviation Rules`, `Must-Haves`, `Test Plan`. `Worker Refs` is pre-populated to include `../story-memory.md`.
4. Update each task's `tasks.yaml` entry: set `spec: tasks/task-NN.md`.
5. Now you can flip status to `executing`.

### tasks.yaml skeleton (applies to both paths)

Entries must set: `id`, `title`, `wave`, `depends_on`, `spec`, `files_modified`, `test_layer`. `test_layer` = the lowest layer that can falsify acceptance (per Rule 1 of the decomposition rules).

**Freedom note**: appending, reordering, or removing tasks is a direct `tasks.yaml` edit. The `omp coding-orchestrator task` command is only for the high-frequency fields (status / worker / reviewer / commit / note).

**Sizing rule**: one task = one vertical slice. If a task touches more than 5 files, split it — but split **vertically** (two smaller features), not **horizontally** (all stores, then all components). See Rule 5 in `references/task-decomposition-rules.md`.

**Self-check before dispatching each wave**: run the checklist at the bottom of `references/task-decomposition-rules.md` against the wave's specs. Revise before dispatching if any answer is "no".

## Execute

For each task (orchestrator dispatches in dependency order), follow the route-decision + prompt-preparation protocol in `references/dispatch-routes.md`. In short:

- Native sub-agent in same runtime → sub-agent route (e.g., Claude Code `Agent()`).
- Different runtime or no sub-agent mechanism → tmux route; load `references/commands.md` for exact tmux commands.
- Parallel: isolate with worktree (sub-agent) or multiple tmux sessions + worktree (tmux).

## Review

After each task's code is written:

1. Flip status to `reviewing` **before** dispatching the reviewer:
   `omp coding-orchestrator task update --story <slug> --id NN --status reviewing --reviewer <id>`
2. Dispatch a reviewer (different from the coder when possible):
   - Write review prompt to `/tmp/orchestrator-review-<NN>.md` (include: task spec path, changed files, diff)
   - Use the same route decision as Execute: sub-agent or tmux
   - Recommended: use a reasoning-focused runtime for review (e.g., Claude for review, Codex for coding)
3. Orchestrator reads the review result and applies **second judgment**:
   - Confirmed issue → orchestrator fixes directly (small fix) or dispatches worker (large fix); flip back to `executing` while the fix is in flight
   - False positive → ignore, add `--note "..."` explaining why
4. When the review is resolved, advance to the Test phase:
   `omp coding-orchestrator task update --story <slug> --id NN --status testing`
   (append `--commit <hash>` for any fix commit produced during review)

## Test & Debug

Sub agent runs tests defined in the task spec's Test Plan.

On failure:
1. Sub agent reads `worker-refs/debugging-guideline.md` (already in task spec's Worker Refs).
2. Follow log-driven debugging: list causes → add diagnostic logs → read logs → narrow scope → fix → clean up.
3. **Iteration limit**: max 3 fix attempts per task.

## Failure Escalation

```
Sub agent fails or 3 attempts exhausted
    → Escalate to a different sub agent
        → Orchestrator takes over (this task only)
```

Each escalation carries: error logs, attempted fixes, current hypothesis.

## Acceptance

For each completed task:
1. Read the task spec's `Must-Haves` section.
2. Verify each `truth` — is the behavior observable?
3. Verify each `artifact` — does the file exist with expected content?
4. Verify each `key_link` — does the regex pattern match?
5. All pass →
   `omp coding-orchestrator task update --story <slug> --id NN --status completed`
   (appends commit hash with `--commit <hash>` when relevant)

When all tasks in `tasks.yaml` show `status: completed` → story complete.

## Compaction Recovery

If context was compressed, read `<PROJECT_ROOT>/stories/.handoff-context` to restore state. Mechanism details: `references/handoff-guideline.md`.

## Storage

`stories/` lives at `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/` — never at orchestrator cwd, never inside the skill repo. Resolution algorithm, hard-rule rationale, and full directory layout: `references/storage-layout.md`. Read this reference before creating the first story file in a new project.
