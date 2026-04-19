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
