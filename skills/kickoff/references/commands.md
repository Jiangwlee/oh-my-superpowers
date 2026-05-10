# Reviewer Dispatch Commands

通过 `omp dispatch` 把 reviewer 派到隔离 runtime（codex / claude / pi）做 cross review 时读本文件。

## When to Read

满足任一条件时读取：

- 当前环境没有原生 sub-agent 机制
- 需要切换到不同 runtime（例如你在 Claude，但要让 codex review）

如果当前 runtime 自带 sub-agent 且任务也打算在同一 runtime 完成，优先用原生机制，不要绕到 `omp dispatch`。多文件 review 默认走 sub-agent（codex / pi 在大 diff 上易 timeout）。

## Runtime Matrix

| Runtime | Prompt 传递 | 模型覆盖 |
|---|---|---|
| Claude | stdin pipe（`omp dispatch` 内部处理） | `--model <name>` |
| Codex | stdin pipe（`omp dispatch` 内部处理） | `--model <name>`（透传 `-m`） |
| Pi | `@${PROMPT_FILE}`（`omp dispatch` 内部处理） | `--model <name>` |

`omp dispatch` 默认带：claude `--no-session-persistence`、codex `--ephemeral`、pi `--no-session`，避免污染本地会话历史。

## Prompt Preparation

reviewer prompt 必须先写入文件，禁止直接作为 bash 参数传递。

```bash
PROMPT_FILE="/tmp/kickoff-review-${STORY_SLUG}.md"
# 三段串接写入：protocol body + story 上下文 + diff
```

参考 `review.md` §Reviewer Input 了解 prompt 三段构成。

## Single Reviewer (spawn + wait)

`omp dispatch run` 一步完成：spawn → wait → ANSI-clean 输出到 stdout。

```bash
CWD="/path/to/project"

# Codex
omp dispatch run codex --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300

# Codex with model override
omp dispatch run codex --prompt-file "$PROMPT_FILE" --cwd "$CWD" --model gpt-5.5 --timeout 300

# Claude
omp dispatch run claude --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300

# Pi
omp dispatch run pi --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300
```

退出码：`0` = 成功（output 在 stdout），`124` = 超时，`1` = worker 错误。

## Live Observation

需要边等边看 reviewer 输出时（大 diff 可能跑较久），先 spawn 拿到 session id，再 tail / wait 分开：

```bash
SID=$(omp dispatch spawn codex --prompt-file "$PROMPT_FILE" --cwd "$CWD" --session-name "review-${STORY_SLUG}")
omp dispatch tail "$SID" --follow &
omp dispatch wait "$SID" --timeout 600
```

## Status / Cleanup

```bash
omp dispatch status                  # 列出所有活跃 omp- session
omp dispatch status omp-review-xxx   # 查询单个（注意带 omp- 前缀）
omp dispatch kill omp-review-xxx     # 显式清理
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
