# Handoff Guideline

Execution-state checkpoint for one story. Read this when writing or recovering `stories/<slug>/.handoff-context`.

---

## Overview

`stories/<YYYY-MM-DD>-<slug>/.handoff-context` is the orchestrator's structured checkpoint. Updated at task granularity so recovery does not depend on replaying chat history.

Canonical schema: `templates/handoff-context.yaml`.

## Write Command

```bash
omp coding-orchestrator handoff update \
  --story-dir <PROJECT_ROOT>/stories \
  --story <slug> \
  --task-id <NN> \
  --phase <executing|reviewing|accepting|advancing> \
  --next-action "<one-line next step>"
```

Optional flags: `--worker-agent-id`, `--reviewer-agent-id`, `--commit`, `--deviation`.

## Update Timing

Update whenever any of these happens:

1. A worker is dispatched.
2. A reviewer is dispatched.
3. A review judgment changes the next step.
4. A task is accepted, or a wave advances.

## Recovery Protocol

When resuming a story:

1. Read `stories/<slug>/.handoff-context`.
2. Trust `next_action` first.
3. Check `current_phase` and the active wave entry.
4. Resume only the in-flight task; do not re-open accepted deviations.

## Field Intent

| Field | Meaning |
|---|---|
| `current_wave` / `current_phase` | Where the orchestrator is right now |
| `wave_state` | Compact ledger for the active and completed waves |
| `pending_dispatches` | Sub-agents currently in flight |
| `deviations_accepted` | Approved spec drift — recovery must not re-judge these |
| `next_action` | First sentence the recovered orchestrator should act on |

## Best Practices

- **Keep it task-granular.** This is a ledger, not a narrative report.
- **Make `next_action` executable** without re-reading the whole story.
- **Record accepted deviations once.** Do not force a recovered session to re-judge closed decisions.
- **Do not duplicate `tasks.yaml`.** Copy only the state needed for recovery.
