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

所有命令的 prompt 必须先写入文件，再喂给 worker。

```bash
PROMPT_FILE="/tmp/brainstorm-review-${SLUG}.md"
OUTPUT="/tmp/brainstorm-review-out-${SLUG}.txt"
SESSION="brainstorm-review-${SLUG}"
CWD="$(git rev-parse --show-toplevel)"
```

`PROMPT_FILE` 内容 = reviewer prompt + design doc + 可选附加，三段拼接。

### Claude

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | claude -p --no-session-persistence --dangerously-skip-permissions 2>&1 | tee ${OUTPUT}; exit"
```

### Codex

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "cat ${PROMPT_FILE} | codex exec - --dangerously-bypass-approvals-and-sandbox 2>&1 | tee ${OUTPUT}; exit"
```

### Pi

```bash
tmux new-session -d -s "$SESSION" -c "$CWD" \
  "pi --no-session -p @${PROMPT_FILE} 2>&1 | tee ${OUTPUT}; exit"
```

### Wait & Collect

```bash
TIMEOUT=300; ELAPSED=0
while tmux has-session -t "$SESSION" 2>/dev/null; do
  [ $ELAPSED -ge $TIMEOUT ] && { tmux kill-session -t "$SESSION"; echo "TIMEOUT" > "$OUTPUT"; break; }
  sleep 5; ELAPSED=$((ELAPSED + 5))
done
cat "$OUTPUT"
```

## Verdict Loop

Reviewer 输出格式见 `assets/spec-document-reviewer-prompt.md`。

| Verdict | 动作 |
|---|---|
| `PASS` | spec 进入 deliver 阶段 |
| `REVISE` with Blocking | 修 Blocking issue → 更新 design doc → 重新 dispatch |
| `REVISE` only Advisory | Blocking 为空时视作通过；Advisory 由 brainstorming 主线判断是否采纳 |

连续 3 轮仍未 PASS → 停下，把 review 报告 + 当前 design doc 提给用户决定（与 SKILL.md `Hard Gate` 表 "Spec review 超 3 轮仍未 PASS" 行一致）。
