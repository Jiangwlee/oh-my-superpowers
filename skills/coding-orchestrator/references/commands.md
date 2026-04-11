# Worker Dispatch Commands

How to spawn coding workers in tmux sessions, wait for completion, and collect output.
Read this when you need to dispatch tasks to external coding agents.

---

## When to Read This File

- You do NOT have a native sub-agent mechanism (e.g., you are running in Codex, Pi, or a non-Claude environment)
- OR you need to dispatch to a runtime different from your own (e.g., you are Claude but need Codex to code)

If you have a native sub-agent mechanism AND the task should run in the same runtime, use that instead.

## Prompt Preparation

**All prompts MUST be written to a file first.** Never pass prompts as bash arguments.

```bash
# Write prompt to a temp file
PROMPT_FILE="/tmp/orchestrator-task-${TASK_ID}.md"
# (orchestrator writes the prompt content to this file)

# For review tasks, include the diff
REVIEW_FILE="/tmp/orchestrator-review-${TASK_ID}.md"
```

## Spawn Commands

### Claude

```bash
SESSION="worker-${TASK_ID}"
OUTPUT="/tmp/orchestrator-out-${TASK_ID}.txt"
CWD="/path/to/project"

tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | claude -p --no-session-persistence --dangerously-skip-permissions 2>&1 | tee ${OUTPUT}; exit"
```

With model override:

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | claude -p --no-session-persistence --dangerously-skip-permissions --model sonnet 2>&1 | tee ${OUTPUT}; exit"
```

### Codex

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee ${OUTPUT}; exit"
```

Note: Codex `exec` reads prompt from stdin. Model is controlled by Codex's own config.

### Pi

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "pi --no-session -p @${PROMPT_FILE} 2>&1 | tee ${OUTPUT}; exit"
```

With model override:

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "pi --no-session -p @${PROMPT_FILE} --model ${MODEL} 2>&1 | tee ${OUTPUT}; exit"
```

## Wait for Completion

```bash
# Poll until session exits (worker done)
TIMEOUT=300
ELAPSED=0
POLL=5

while tmux has-session -t "$SESSION" 2>/dev/null; do
  if [ $ELAPSED -ge $TIMEOUT ]; then
    tmux kill-session -t "$SESSION" 2>/dev/null
    echo "TIMEOUT" > "$OUTPUT"
    break
  fi
  sleep $POLL
  ELAPSED=$((ELAPSED + POLL))
done
```

## Collect Output

```bash
# Read the output file
cat "$OUTPUT"

# Clean up ANSI escape codes if needed
sed 's/\x1b\[[0-9;]*m//g' "$OUTPUT" > "${OUTPUT}.clean"
```

## Parallel Execution

For independent tasks, spawn multiple sessions and wait for all:

```bash
# Spawn task-01 and task-03 in parallel (different worktrees)
tmux new-session -d -s "worker-01" -c ".worktrees/w01" \
  "cat /tmp/task-01.md | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee /tmp/out-01.txt; exit"

tmux new-session -d -s "worker-03" -c ".worktrees/w03" \
  "cat /tmp/task-03.md | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee /tmp/out-03.txt; exit"

# Wait for all
while tmux has-session -t "worker-01" 2>/dev/null || \
      tmux has-session -t "worker-03" 2>/dev/null; do
  sleep 5
done
```

### Worktree Setup (for parallel coding in same repo)

```bash
git worktree add .worktrees/w01 -b orchestrator/task-01
git worktree add .worktrees/w03 -b orchestrator/task-03
```

### Worktree Merge (after parallel tasks complete)

```bash
git merge --no-ff orchestrator/task-01
git merge --no-ff orchestrator/task-03

# Clean up
git worktree remove .worktrees/w01
git worktree remove .worktrees/w03
git branch -d orchestrator/task-01 orchestrator/task-03
```

If merge conflicts occur, STOP and report to user. Do not auto-resolve.

## Adding New Runtimes

To support a new coding agent, add a section above following this pattern:

```
### <RuntimeName>

\`\`\`bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "<command-that-reads-prompt-from-file-and-writes-output> 2>&1 | tee ${OUTPUT}; exit"
\`\`\`
```

Requirements for any runtime command:
1. Read prompt from file (stdin pipe or `@file` syntax)
2. Write output to stdout (captured by `tee`)
3. Run non-interactively (no human confirmation prompts)
4. Exit when done (tmux session auto-closes)
