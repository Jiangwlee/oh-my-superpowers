# Handoff Guideline

How the orchestrator preserves state across context compaction events.
Read this when performing a manual handoff or recovering after compaction.

---

## Overview

Context compaction is inevitable in long sessions. This skill uses two mechanisms
to survive it without losing progress:

1. **Automatic**: PreCompact + PostCompact hooks write/read state files
2. **Manual**: Orchestrator proactively saves state before compaction hits

## Automatic Handoff (Hooks)

### PreCompact Hook

Triggered automatically before Claude compresses context.

**What it runs**: `omp coding-orchestrator handoff --auto --story-dir ./stories`
(dispatches to `scripts/handoff.py`). It scans every active story directory,
reads each `tasks.yaml` (single source of truth for status), and writes a
`handoff.md` per story containing:

- Current story progress (which tasks are done, in progress, pending)
- Active task details (what sub agent is working on, current status)
- Blocking issues (if any)

### PostCompact Hook

Triggered automatically after context compression completes.

**What it runs**: `omp coding-orchestrator restore --story-dir ./stories`
(dispatches to `scripts/restore.py`). It reads the freshest `handoff.md`
and writes a consolidated recovery file to `<PROJECT_ROOT>/stories/.handoff-context`.

**Important**: PostCompact stdout does NOT inject into Claude's context.
The orchestrator must **actively read** `<PROJECT_ROOT>/stories/.handoff-context` to recover.

### Recovery Protocol

After compaction, the orchestrator should:

1. Read `<PROJECT_ROOT>/stories/.handoff-context`
2. Understand current story progress
3. Resume from where the last task left off
4. Do NOT re-dispatch completed tasks

## Manual Handoff

### When to Trigger

Proactively save state when context usage reaches **60-85%**. Do NOT wait
for automatic compaction (~92%) — by then, valuable reasoning context is
already being compressed.

**Signs you should handoff soon:**
- You've dispatched multiple sub agents and processed their results
- You've accumulated significant review judgments and decisions
- The session has been running for a long time with many tool calls

### How to Trigger

The orchestrator writes the handoff file directly:

```
<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/handoff.md
```

### Handoff File Format

```markdown
# Handoff: <YYYY-MM-DD>-<slug>

**Timestamp**: <ISO 8601>
**Context usage**: <approximate %>

## Story Progress

| Task | Status | Notes |
|------|--------|-------|
| task-01 | completed | commit abc1234 |
| task-02 | reviewing | review result: 2 issues found, 1 confirmed |
| task-03 | pending | depends on task-02 |

## Active Task Details

**Task**: task-02 — <name>
**Phase**: Review
**Current state**: Codex review returned 2 issues. Issue #1 confirmed (type mismatch
in auth handler). Issue #2 is false positive (existing pattern, not a bug).
**Next action**: Fix issue #1, then re-run tests.

## Key Decisions Made

- Chose JWT over session cookies for auth (design doc section 3.2)
- Split user-profile into two tasks because it touches both API and DB schema
- task-01 review: accepted 2 of 3 Codex suggestions, rejected #3 as false positive

## Blocking Issues

- None currently

## Next Steps

1. Fix confirmed review issue in task-02
2. Run task-02 tests
3. Accept task-02
4. Dispatch task-03
```

## .handoff-context File Format

The consolidated recovery file at `<PROJECT_ROOT>/stories/.handoff-context` is a simplified
version meant for quick orientation after compaction:

```markdown
# Coding Orchestrator — Recovery Context

**Story**: <YYYY-MM-DD>-<slug>
**Last updated**: <ISO 8601>
**Source**: <PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/handoff.md

## Quick Status

- Total tasks: N
- Completed: X
- In progress: Y (task-NN: <phase>)
- Pending: Z

## Resume From

**Task**: task-NN
**Phase**: <Execute|Review|Test|Acceptance>
**Action needed**: <one sentence describing the immediate next action>

## Critical Context

<key decisions and constraints that would be lost in compaction>
```

## Best Practices

1. **Keep handoff files concise** — they exist to restore orientation, not replay history
2. **Focus on decisions** — code changes are in git, but WHY you chose approach A over B is lost in compaction
3. **Include blocking context** — if a task is stuck, explain why so the recovered session doesn't re-discover the same dead end
4. **Don't handoff mid-thought** — complete the current review judgment or dispatch before saving state
