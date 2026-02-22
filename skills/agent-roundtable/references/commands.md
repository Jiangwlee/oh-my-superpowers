# Commands Reference

所有路径使用 `{SKILL_DIR}` 表示 skill 根目录（运行时替换为实际路径）。
`--memory-root .memory` 是统一默认值，所有脚本共用。

---

## 1) init_session

创建新会话，返回 `session_id`。

```bash
python3 {SKILL_DIR}/scripts/init_session.py \
  --memory-root .memory \
  --topic "讨论支付网关重构方案" \
  --participants user,codex,claude-code,opencode \
  --background-file ./discussion.md
```

输出：JSON，包含 `session_id`、`session_dir`、`session_file`。

`--memory-root` 兼容两种写法（效果相同）：
- `--memory-root .memory`
- `--memory-root .memory/agent-roundtable`

---

## 2) append_message

向 session 追加一条发言。

```bash
python3 {SKILL_DIR}/scripts/append_message.py \
  --memory-root .memory \
  --session-id <session-id> \
  --speaker codex \
  --role agent \
  --message-type comment \
  --message "建议先拆分 adapter 层，再迁移路由。"
```

`--message-type` 可选值：`kickoff` `context` `comment` `proposal` `objection` `support` `question` `summary` `decision` `action`

可选参数：
- `--reply-to-index 12`
- `--tags architecture,rollback`
- `--extra-json '{"priority":"high"}'`

---

## 3) read_updates

增量读取（只读上次游标之后的消息）。

```bash
# 从指定 index 读取
python3 {SKILL_DIR}/scripts/read_updates.py \
  --memory-root .memory \
  --session-id <session-id> \
  --since-index 18

# 从游标读取并持久化新游标（推荐）
python3 {SKILL_DIR}/scripts/read_updates.py \
  --memory-root .memory \
  --session-id <session-id> \
  --consumer codex \
  --save-cursor
```

可选过滤：`--speaker user` `--role agent` `--message-type decision` `--limit 50`

---

## 4) spawn_agent

在 tmux 中启动外部 agent，注入初始参与提示。每个 agent 只需调用一次。

```bash
python3 {SKILL_DIR}/scripts/spawn_agent.py \
  --memory-root .memory \
  --session-id <session-id> \
  --agent codex \
  --agent-type codex \
  --workdir /path/to/project
```

`--agent-type` 可选值：`claude-code` `codex` `opencode`

可选参数：
- `--wait-idle`：等待 agent 空闲后再返回
- `--idle-timeout 60`：等待超时秒数（默认 60）
- `--extra-args "..."`：额外传给 agent CLI 的参数

**前置条件**：需要 tmux 已安装，且对应 agent CLI 可用（`codex`、`opencode`）。

---

## 5) inject_round

向已 spawn 的 agent 注入本轮讨论提示，并等待其 append 回复。

```bash
python3 {SKILL_DIR}/scripts/inject_round.py \
  --memory-root .memory \
  --session-id <session-id> \
  --agent codex \
  --round 1 \
  --prompt "请针对以下方案给出你的看法：..." \
  --max-wait 180
```

可选参数：
- `--max-wait 300`：等待 agent 回复的最长秒数（默认 300）
- `--check-interval 2.0`：检查间隔秒数（默认 2.0）
- `--no-interrupt`：注入前不发送 Ctrl+C

**前置条件**：该 agent 必须已通过 `spawn_agent` 启动。

---

## 6) orchestrate_discussion（全自动编排）

一键完成：创建 session → spawn agents → 多轮 inject → 收敛检测。

```bash
python3 {SKILL_DIR}/scripts/orchestrate_discussion.py \
  --memory-root .memory \
  --topic "讨论话题" \
  --agents "codex:codex,opencode:opencode" \
  --background-file ./background.md \
  --max-rounds 5 \
  --round-timeout 300
```

恢复已有 session（不重新 spawn）：

```bash
python3 {SKILL_DIR}/scripts/orchestrate_discussion.py \
  --memory-root .memory \
  --session-id <session-id> \
  --skip-spawn
```

可选参数：
- `--mode sequential|parallel`：发言顺序（默认 sequential 轮流）
- `--no-auto-close`：收敛后不自动关闭 session
- `--dry-run`：预演，不实际执行

---

## 7) close_session（Mode B 必须步骤）

关闭讨论会话，写入 `session_close` 事件并 kill 所有关联的 tmux session。幂等：重复执行不报错。

```bash
python3 {SKILL_DIR}/scripts/close_session.py \
  --memory-root .memory \
  --session-id <session-id>
```

可选参数：
- `--dry-run`：预演，显示会做什么，不实际执行
- `--keep-tmux`：只更新 session 状态，不 kill tmux session
- `--force`：对已关闭的 session 强制重新执行清理

**关键**：tmux session 名从 `meta.json` 的 `agents[*].tmux_session` 读取，不依赖命名规则推断。

---

## 8) cleanup_stale_sessions（维护工具）

扫描所有 session，清理异常退出后残留的 tmux session。

```bash
# 预览（不实际执行）
python3 {SKILL_DIR}/scripts/cleanup_stale_sessions.py \
  --memory-root .memory \
  --dry-run

# 实际清理所有已关闭 session 的残留 tmux
python3 {SKILL_DIR}/scripts/cleanup_stale_sessions.py \
  --memory-root .memory

# 强制清理所有 session（包括状态为 open 的）
python3 {SKILL_DIR}/scripts/cleanup_stale_sessions.py \
  --memory-root .memory \
  --force

# 只清理某一个 session
python3 {SKILL_DIR}/scripts/cleanup_stale_sessions.py \
  --memory-root .memory \
  --session-id <session-id> \
  --force
```

可选参数：
- `--dry-run`：预演，不实际 kill
- `--force`：同时清理状态为 open 的 session（默认只清理 closed）
- `--session-id`：限定到单个 session

---

## 9) list_sessions

列出所有会话（按最后更新时间排序）。

```bash
python3 {SKILL_DIR}/scripts/list_sessions.py --memory-root .memory
```

---

## 10) watch_session（TUI 输出）

```bash
# 列出所有会话
python3 {SKILL_DIR}/scripts/watch_session.py --memory-root .memory

# 查看某会话全量内容
python3 {SKILL_DIR}/scripts/watch_session.py \
  --memory-root .memory \
  --session-id <session-id>

# 只看最后 10 条
python3 {SKILL_DIR}/scripts/watch_session.py \
  --memory-root .memory \
  --session-id <session-id> \
  --tail 10

# 实时监听新消息（Ctrl-C 退出）
python3 {SKILL_DIR}/scripts/watch_session.py \
  --memory-root .memory \
  --session-id <session-id> \
  --follow
```

---

## JSONL Event Schema

```json
{
  "index": 3,
  "timestamp": "2026-02-20T10:17:03Z",
  "session_id": "20260220-101500-payment-gateway",
  "topic": "讨论支付网关重构方案",
  "role": "agent",
  "speaker": "codex",
  "message_type": "comment",
  "message": "建议先拆分 adapter 层，再迁移路由。",
  "reply_to_index": 2,
  "tags": ["architecture"],
  "extra": {"tool": "codex"}
}
```

字段说明：
- `index`：session 内严格递增整数
- `timestamp`：UTC RFC3339
- `role`：`user` | `agent` | `system`
- `message_type`：见 append_message 说明
- `reply_to_index`：可选，跨消息引用
