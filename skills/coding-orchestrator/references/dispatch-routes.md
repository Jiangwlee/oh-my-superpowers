# Dispatch Routes

Detailed protocol for the Execute step.

## Route Decision

| Condition | Route | Example |
|-----------|-------|---------|
| You have native sub-agent AND task runs in same runtime | **Sub-agent** | Claude Code's `Agent()` tool |
| You need a different runtime OR no sub-agent mechanism | **tmux** | Read `commands.md` |

## Prompt Preparation (both routes)

Write a prompt file at `/tmp/orchestrator-task-<NN>.md` containing:
1. Path to the task spec file: `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md`
2. One sentence: "Read the spec, then read every file in its Worker Refs and Read First sections, then execute."

The task spec's **Worker Refs** section lists all behavioral docs (constitution, worker-guideline, etc.) the worker must read.

**No-spec fallback**: only when there is no spec file (e.g., urgent hotfix), inject the task description directly into the prompt.

## Sub-agent Route

Dispatch using your runtime's native sub-agent mechanism. Pass the prompt file path.

## tmux Route

Read `commands.md` for exact commands. Key steps:
1. Write prompt to file
2. Spawn tmux session with the appropriate runtime command
3. Poll until session exits
4. Read output file

## Parallel execution

Tasks without dependencies may run in parallel.
- Sub-agent route: use your runtime's isolation mechanism (e.g., worktree)
- tmux route: spawn multiple tmux sessions + git worktree (see `commands.md`)

---

## Review Protocol

After each task's code is written:

1. Flip status to `reviewing` before dispatching the reviewer:
   `omp coding-orchestrator task update --story <slug> --id <NN> --status reviewing --reviewer <id>`
2. Write review prompt to `/tmp/orchestrator-review-<NN>.md` (include: task spec path, changed files, diff). Dispatch using the same route decision as Execute. Prefer a reasoning-focused runtime for review.
3. Orchestrator applies second judgment to the review result:
   - Confirmed issue → fix directly (small) or dispatch worker (large); flip back to `executing` while fix is in flight
   - False positive → ignore; add `--note "..."` explaining why
4. Advance to Test phase:
   `omp coding-orchestrator task update --story <slug> --id <NN> --status testing`
   (append `--commit <hash>` for any fix commit produced during review)

---

## Test & Debug

Sub-agent runs tests defined in the task spec's Test Plan.

On failure:
1. Read `worker-refs/debugging-guideline.md`: list causes → add diagnostic logs → read logs → narrow scope → fix → clean up.
2. **Iteration limit**: max 3 fix attempts per task.

### Failure Escalation

```
Sub-agent fails or 3 attempts exhausted
    → Escalate to a different sub-agent
        → Orchestrator takes over (this task only)
```

Each escalation carries: error logs, attempted fixes, current hypothesis.
