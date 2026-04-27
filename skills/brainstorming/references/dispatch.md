# Spec Reviewer Dispatch

派遣 spec-document-reviewer 时读取本文件。Spec review 是 S2 Step 5 / S3 Step 4 的硬门槛。

## Hard Constraint

Reviewer 必须在**隔离上下文**中运行。

| 优先级 | 方式 | 说明 |
|---|---|---|
| 1 | **跨工具 Tmux** | 默认。当前在 Claude → 派 OpenAI Codex / Pi；当前在 Codex → 派 Claude |
| 2 | **Sub Agent** | 跨工具派遣失败或当前 runtime 不支持时降级使用，派同 runtime 内的独立 sub-agent |

主上下文自评禁止。Brainstorming 主线可以修复 review 反馈，但不得自任 reviewer。

## Reviewer Input

Reviewer 接收三段串接内容：

1. **Reviewer prompt**：`assets/spec-document-reviewer-prompt.md` 全文
2. **Design doc**：本轮产出的 `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md` 全文
3. **可选附加**：用户在 brainstorming 过程中明确表达的约束（如"必须保留向后兼容"、"DB schema 不能改"），原话引用

## Spawn Commands

Prompt 必须先写入文件，再喂给 worker。

```bash
PROMPT_FILE="/tmp/brainstorm-review-${SLUG}.md"
CWD="$(git rev-parse --show-toplevel)"
```

`PROMPT_FILE` 内容 = reviewer prompt + design doc + 可选附加，三段拼接。

`omp dispatch run` 一步完成 spawn → wait → 输出 ANSI-clean 结果到 stdout，session 名带 `omp-` 前缀且全局唯一，不会与其他派遣冲突。

### Claude

```bash
omp dispatch run claude --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300
```

### Codex

```bash
omp dispatch run codex --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300
```

### Pi

```bash
omp dispatch run pi --prompt-file "$PROMPT_FILE" --cwd "$CWD" --timeout 300
```

退出码：`0` = PASS/REVISE 已写入 stdout；`124` = 超时；`1` = worker 错误。

### Live Observation（可选）

如需边等边看 reviewer 输出，先 spawn 再 tail：

```bash
SID=$(omp dispatch spawn claude --prompt-file "$PROMPT_FILE" --cwd "$CWD" --session-name "brainstorm-review-${SLUG}")
omp dispatch tail "$SID" --follow &
omp dispatch wait "$SID" --timeout 300
```

## Verdict Loop

Reviewer 输出格式见 `assets/spec-document-reviewer-prompt.md`。

| Verdict | 动作 |
|---|---|
| `PASS` | spec 进入 deliver 阶段 |
| `REVISE` with Blocking | 修 Blocking issue → 更新 design doc → 重新 dispatch |
| `REVISE` only Advisory | Blocking 为空时视作通过；Advisory 由 brainstorming 主线判断是否采纳 |

连续 3 轮仍未 PASS → 停下，把 review 报告 + 当前 design doc 提给用户决定（与 SKILL.md `Hard Gate` 表 "Spec review 超 3 轮仍未 PASS" 行一致）。
