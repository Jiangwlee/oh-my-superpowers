# Dispatch Routes

Protocol for the Execute step.

## Capability Routing

Route workers and reviewers by capability level, not by gut feel.

| Level | Use for | Claude | Codex |
|---|---|---|---|
| L1 | templates, low-risk mechanical work, subagents | Haiku 4.5 | gpt-5.4-mini |
| L2 | standard coding and review | Sonnet 4.6 | gpt-5.4-mini or gpt-5.3-codex |
| L3 | deep reasoning, concurrency, async boundaries, skeleton review gate | Opus 4.7 | gpt-5.4 |
| L4 | frontier-only coding spikes | — | gpt-5.4 |

Default to the same provider family for worker and reviewer. Cross-provider review is **off by default** — enable only when the user explicitly requests it.

Codex model guidance:

- `gpt-5.4-mini` — high-volume narrow subtasks.
- `gpt-5.4` — main reasoning-heavy worker/reviewer path.
- `gpt-5.3-codex` — L2 fallback; coding-specialized middle tier.

## Task type → capability level

| Signal | Route |
|---|---|
| Simple template / docs-only touch | L1 |
| Routine feature / fix within one subsystem | L2 |
| Concurrency, signals, async boundaries, lifecycle wiring, task-skeleton review | L3 |
| Novel frontier coding or investigation with no proven local pattern | L4 |

## Route decision

| Condition | Route | Example |
|---|---|---|
| Native sub-agent AND task runs in same runtime | **Sub-agent** | Claude Code's `Agent()` tool |
| Different runtime needed OR no sub-agent mechanism | **tmux** | See `references/commands.md` |

## Prompt preparation (both routes)

Write a prompt file at `/tmp/orchestrator-task-<NN>.md` containing:

1. The path to the task spec: `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md`.
2. One sentence: "Read the spec, then read every file in its Worker Refs and Read First sections, then execute."

The spec's **Worker Refs** section lists every behavioral doc (constitution, worker-guideline, etc.) the worker must read.

**No-spec fallback**: only when there is no spec file (e.g., urgent hotfix), inject the task description directly into the prompt.

## Sub-agent route

Dispatch using your runtime's native sub-agent mechanism. Pass the prompt file path.

## tmux route

See `references/commands.md` for the exact commands. Key steps:

1. Write prompt to file.
2. Spawn the tmux session with the appropriate runtime command.
3. Poll until the session exits.
4. Read the output file.

## Parallel execution

Tasks without dependencies may run in parallel.

- **Sub-agent route** — use your runtime's isolation mechanism (e.g., worktree).
- **tmux route** — spawn multiple tmux sessions + git worktree (see `references/commands.md`).

---

## Review Protocol

After each task's code is written:

1. Flip status to `reviewing` before dispatching the reviewer:
   `omp coding-orchestrator task update --story-dir <PROJECT_ROOT>/stories --story <slug> --id <NN> --status reviewing --reviewer <id>`
2. Generate the task context fragment:
   `omp coding-orchestrator review create --story-dir <PROJECT_ROOT>/stories --story <slug> --task-id <NN> [--additional <str>]`
   Read the `code-reviewer` agent (see SKILL.md Agents table), pass `<agent protocol body>\n\n<task context>` as the prompt. Prefer an L2+ reasoning-focused runtime for review.
3. Apply orchestrator second judgment to the review result:
   - **Confirmed issue** → dispatch worker revision; flip back to `executing` while the fix is in flight.
   - **False positive** → ignore; add `--note "..."` explaining why.
4. Advance to Test phase:
   `omp coding-orchestrator task update --story-dir <PROJECT_ROOT>/stories --story <slug> --id <NN> --status testing`
   (append `--commit <hash>` for any fix commit produced during review).

---

## Test & Debug

The sub-agent runs the tests defined in the task spec's Test Plan.

On failure:

1. Follow `worker-refs/debugging-guideline.md` — list causes → add diagnostic logs → read logs → narrow scope → fix → clean up.
2. **Iteration limit**: max 3 fix attempts per task.

### Failure escalation

```
Sub-agent fails or 3 attempts exhausted
    → Escalate to a different sub-agent
        → Escalate to a stronger worker or different runtime
            → If still blocked, pause and report the blocker to the user
```

Each escalation carries: error logs, attempted fixes, current hypothesis.
