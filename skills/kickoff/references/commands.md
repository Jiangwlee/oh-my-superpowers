# Worker Dispatch Commands

当 orchestrator 需要用 tmux 派发外部 runtime 时，读取本文件。它只解决一件事：**如何启动 worker、等待结束、收集输出。**

## When to Read

满足任一条件时读取：

- 当前环境没有原生 sub-agent 机制
- 需要切换到不同 runtime（例如你在 Claude，但要用 Codex）

如果当前 runtime 自带 sub-agent，且任务也打算在同一 runtime 里完成，优先用原生机制，不要绕到 tmux。

## Runtime Matrix

| Runtime | Prompt source | Model override |
|---|---|---|
| Claude | stdin pipe | `--model <name>` |
| Codex | stdin pipe (`exec -`) | 由 Codex 配置控制 |
| Pi | `@${PROMPT_FILE}` | `--model <name>` |

## Prompt Preparation

所有 prompt 必须先写入文件，禁止直接作为 bash 参数传递。

```bash
PROMPT_FILE="/tmp/kickoff-task-${TASK_ID}.md"
# 先把 prompt 写到文件，再启动 worker
# review prompt 也同理：protocol + task.md + diff
```

## Spawn Commands

### Claude

```bash
SESSION="worker-${TASK_ID}"
OUTPUT="/tmp/kickoff-out-${TASK_ID}.txt"
CWD="/path/to/project"

tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | claude -p --no-session-persistence --dangerously-skip-permissions 2>&1 | tee ${OUTPUT}; exit"
```

带 model override：

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | claude -p --no-session-persistence --dangerously-skip-permissions --model sonnet 2>&1 | tee ${OUTPUT}; exit"
```

### Codex

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee ${OUTPUT}; exit"
```

`codex exec` 从 stdin 读取 prompt；模型由 Codex 配置决定。

### Pi

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "pi --no-session -p @${PROMPT_FILE} 2>&1 | tee ${OUTPUT}; exit"
```

带 model override：

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "pi --no-session -p @${PROMPT_FILE} --model ${MODEL} 2>&1 | tee ${OUTPUT}; exit"
```

## Wait for Completion

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

## Collect Output

```bash
cat "$OUTPUT"

# 如需去掉 ANSI 转义
sed 's/\x1b\[[0-9;]*m//g' "$OUTPUT" > "${OUTPUT}.clean"
```

## Parallel Execution

只在任务彼此独立时并行。

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

### Worktree Setup

```bash
git worktree add .worktrees/w01 -b kickoff/task-01
git worktree add .worktrees/w03 -b kickoff/task-03
```

### Worktree Merge

```bash
git merge --no-ff kickoff/task-01
git merge --no-ff kickoff/task-03

git worktree remove .worktrees/w01
git worktree remove .worktrees/w03
git branch -d kickoff/task-01 kickoff/task-03
```

发生 merge conflict 时，立即停止并报告用户。不要自动解冲突。

## Adding a New Runtime

新增 runtime 时，在 **Spawn Commands** 下追加同形态章节：

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "<command-that-reads-prompt-from-file-and-writes-output> 2>&1 | tee ${OUTPUT}; exit"
```

新增命令必须满足：

1. 从文件读取 prompt（stdin pipe 或 `@file` 都可以）
2. 输出写到 stdout，便于 `tee` 捕获
3. 可非交互运行
4. 结束后自动退出，使 tmux session 关闭
