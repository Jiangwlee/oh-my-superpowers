# Handoff Guideline

How the orchestrator preserves execution state inside one story.
Read this when updating or recovering `stories/<slug>/.handoff-context`.

---

## Overview

`stories/<YYYY-MM-DD>-<slug>/.handoff-context` is the orchestrator's structured checkpoint file.
It is updated at task granularity so recovery does not depend on replaying long chat history.

Write it with:

```bash
omp coding-orchestrator handoff update \
  --story <slug> \
  --task-id <NN> \
  --phase <executing|reviewing|accepting|advancing> \
  --next-action "<one-line next step>"
```

Optional fields:

- `--worker-agent-id`
- `--reviewer-agent-id`
- `--commit`
- `--deviation`

The canonical schema lives in `templates/handoff-context.yaml`.

## Recovery Protocol

When resuming a story:

1. Read `stories/<slug>/.handoff-context`
2. Trust `next_action` first
3. Check `current_phase` and the current wave entry
4. Resume only the in-flight task; do not rediscover already accepted deviations

## Update Timing

Update the handoff context whenever any of these happens:

1. A worker is dispatched
2. A reviewer is dispatched
3. A review judgment changes the next step
4. A task is accepted or a wave advances

## Field Intent

- `current_wave` / `current_phase`: where the orchestrator is right now
- `wave_state`: compact ledger for the active and completed waves
- `pending_dispatches`: sub-agents currently in flight
- `deviations_accepted`: approved spec drift so recovery does not reopen closed decisions
- `next_action`: the first sentence the recovered orchestrator should act on

## Best Practices

1. **Keep the file task-granular** — this is a checkpoint ledger, not a narrative report.
2. **Prefer concrete next actions** — `next_action` should be executable without rereading the whole story.
3. **Record accepted deviations once** — don't force a recovered session to re-judge the same scope change.
4. **Do not duplicate `tasks.yaml` wholesale** — copy only the state needed for recovery.
