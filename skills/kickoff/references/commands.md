# Worker Dispatch Commands

通过 `omp dispatch` 启动外部 runtime worker、等待完成、收集输出的命令参考。

## When to Read

满足任一条件时读取：

- 当前环境没有原生 sub-agent 机制
- 需要切换到不同 runtime（例如你在 Claude，但要用 Codex）

如果当前 runtime 自带 sub-agent，且任务也打算在同一 runtime 里完成，优先用原生机制，不要绕到 `omp dispatch`。

## Runtime Matrix

| Runtime | Prompt 传递 | 模型覆盖 |
|---|---|---|
| Claude | stdin pipe（`omp dispatch` 内部处理） | `--model <name>` |
| Codex | stdin pipe（`omp dispatch` 内部处理） | `--model <name>`（透传 `-m`） |
| Pi | `@${PROMPT_FILE}`（`omp dispatch` 内部处理） | `--model <name>` |

`omp dispatch` 默认带：claude `--no-session-persistence`、codex `--ephemeral`、pi `--no-session`，避免污染本地会话历史。

## Prompt Preparation

所有 prompt 必须先写入文件，禁止直接作为 bash 参数传递。

```bash
PROMPT_FILE="/tmp/kickoff-task-${TASK_ID}.md"
# 先把 prompt 写到文件，再启动 worker
# review prompt 也同理：protocol + task.md + diff
```

## Single Worker (spawn + wait)

`omp dispatch run` 一步完成：spawn → wait → ANSI-clean 输出到 stdout。

```bash
CWD="/path/to/project"

# Claude
omp dispatch run claude --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300

# Claude with model override
omp dispatch run claude --prompt-file "$PROMPT_FILE" --cwd "$CWD" --model sonnet --timeout 300

# Codex
omp dispatch run codex --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300

# Pi
omp dispatch run pi --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300

# Pi with model override
omp dispatch run pi --prompt-file "$PROMPT_FILE" --cwd "$CWD" --model "$MODEL" --timeout 300
```

退出码：`0` = 成功（output 在 stdout），`124` = 超时，`1` = worker 错误。

## Live Observation

需要边等边看 worker 输出时，先 spawn 拿到 session id，再 tail/wait 分开：

```bash
SID=$(omp dispatch spawn codex --prompt-file "$PROMPT_FILE" --cwd "$CWD" --session-name "worker-${TASK_ID}")
omp dispatch tail "$SID" --follow &
omp dispatch wait "$SID" --timeout 300
```

## Parallel Execution

只在任务彼此独立时并行。每个 worker 给一个唯一 session 名，最后用 `omp dispatch wait --mode all`（或 `any`）等待。

```bash
SID1=$(omp dispatch spawn codex --prompt-file /tmp/task-01.md --cwd .worktrees/w01 --session-name "worker-01")
SID3=$(omp dispatch spawn codex --prompt-file /tmp/task-03.md --cwd .worktrees/w03 --session-name "worker-03")

# 等所有完成
omp dispatch wait "$SID1" "$SID3" --mode all --timeout 600

# 或：等任一完成（其余继续后台运行）
# omp dispatch wait "$SID1" "$SID3" --mode any --timeout 600
```

各 worker 输出可单独取：

```bash
omp dispatch tail "$SID1"
omp dispatch tail "$SID3"
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

## Status / Cleanup

```bash
omp dispatch status                    # 列出所有活跃 omp- session
omp dispatch status omp-worker-01      # 查询单个（注意要带 omp- 前缀）
omp dispatch kill omp-worker-01        # 显式清理
```

## Adding a New Runtime

新增 runtime 时，扩展 `lib/dispatch/runtime.py` 的 `build_runtime_command()`：

1. 在 `VALID_RUNTIMES` 中加入新名称
2. 在 `build_runtime_command()` 增加 `case` 分支，构造 `cat $prompt_file | <new-runtime> ...` 命令
3. 在 `tests/lib/dispatch/test_runtime.py` 加测试

新 runtime 的 CLI 必须满足：

1. 从文件读取 prompt（stdin pipe 或 `@file` 都可以）
2. 输出写到 stdout，便于 `tee` 捕获
3. 可非交互运行
4. 结束后自动退出，使 tmux session 关闭
