# Worker Dispatch Commands

How to spawn coding workers in tmux sessions, wait for completion, and collect output. Read this when you need to dispatch to an external runtime.

---

## When to read this file

- You have no native sub-agent mechanism (you are running in Codex, Pi, or a non-Claude environment).
- OR you need a different runtime from your own (e.g., you are Claude but need Codex to code).

If you have a native sub-agent mechanism AND the task runs in the same runtime, use that instead.

## Runtime matrix

| Runtime | Prompt source | Model override |
|---|---|---|
| Claude | stdin pipe | `--model <name>` |
| Codex | stdin pipe (`exec -`) | controlled by Codex config |
| Pi | `@${PROMPT_FILE}` | `--model <name>` |

## Prompt preparation

**All prompts MUST be written to a file first.** Never pass prompts as bash arguments.

```bash
PROMPT_FILE="/tmp/supervisor-task-${TASK_ID}.md"
# supervisor writes the prompt content to this file

# For review tasks, include the diff
REVIEW_FILE="/tmp/supervisor-review-${TASK_ID}.md"
```

## Spawn commands

### Claude

```bash
SESSION="worker-${TASK_ID}"
OUTPUT="/tmp/supervisor-out-${TASK_ID}.txt"
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

`codex exec` reads the prompt from stdin. Model is controlled by Codex config.

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

## Wait for completion

```bash
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

## Collect output

```bash
cat "$OUTPUT"

# Clean ANSI escapes if needed
sed 's/\x1b\[[0-9;]*m//g' "$OUTPUT" > "${OUTPUT}.clean"
```

## Parallel execution

Spawn multiple sessions (independent tasks only) and wait for all:

```bash
tmux new-session -d -s "worker-01" -c ".worktrees/w01" \
  "cat /tmp/task-01.md | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee /tmp/out-01.txt; exit"

tmux new-session -d -s "worker-03" -c ".worktrees/w03" \
  "cat /tmp/task-03.md | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee /tmp/out-03.txt; exit"

while tmux has-session -t "worker-01" 2>/dev/null || \
      tmux has-session -t "worker-03" 2>/dev/null; do
  sleep 5
done
```

### Worktree setup

```bash
git worktree add .worktrees/w01 -b supervisor/task-01
git worktree add .worktrees/w03 -b supervisor/task-03
```

### Worktree merge

```bash
git merge --no-ff supervisor/task-01
git merge --no-ff supervisor/task-03

git worktree remove .worktrees/w01
git worktree remove .worktrees/w03
git branch -d supervisor/task-01 supervisor/task-03
```

On merge conflict, STOP and report to the user. Do not auto-resolve.

## Adding a new runtime

Append a section under **Spawn commands** using this shape:

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "<command-that-reads-prompt-from-file-and-writes-output> 2>&1 | tee ${OUTPUT}; exit"
```

A runtime command must:

1. Read the prompt from a file (stdin pipe or `@file` syntax).
2. Write output to stdout (captured by `tee`).
3. Run non-interactively (no human confirmation prompts).
4. Exit when done (tmux session auto-closes).
