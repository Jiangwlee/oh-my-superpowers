# Commands And Schema

## 1) Init session

```bash
python3 skills/vibe-coding-discussion/scripts/init_session.py \
  --memory-root .memory \
  --topic "讨论支付网关重构方案" \
  --participants user,codex,claude-code,opencode \
  --background-file ./discussion.md
```

Output:
- Prints JSON with `session_id`, `session_dir`, and `session_file`.
- If background is provided, script writes a session-local snapshot:
  - `<session-dir>/background.md`
  - `meta.json.background_file = "background.md"`

`--memory-root` compatibility:
- `--memory-root .memory`
- `--memory-root .memory/vibe-coding-discussion`
Both are accepted and map to the same layout.

## 2) Append one message

```bash
python3 skills/vibe-coding-discussion/scripts/append_message.py \
  --memory-root .memory \
  --session-id 20260220-101500-payment-gateway \
  --speaker codex \
  --role agent \
  --message-type comment \
  --message "建议先拆分 adapter 层，再迁移路由。"
```

Optional metadata fields:
- `--reply-to-index 12`
- `--tags architecture,rollback`
- `--extra-json '{"priority":"high","tool":"codex"}'`

## 3) Read incremental updates

Read from explicit index:

```bash
python3 skills/vibe-coding-discussion/scripts/read_updates.py \
  --memory-root .memory \
  --session-id 20260220-101500-payment-gateway \
  --since-index 18
```

Read from consumer cursor and persist new cursor:

```bash
python3 skills/vibe-coding-discussion/scripts/read_updates.py \
  --memory-root .memory \
  --session-id 20260220-101500-payment-gateway \
  --consumer codex \
  --save-cursor
```

Optional filters:
- `--speaker user`
- `--role agent`
- `--message-type decision`
- `--limit 50`

## 4) List sessions

Sessions are sorted by **last update time** (most recent first), not creation time.

```bash
python3 skills/vibe-coding-discussion/scripts/list_sessions.py --memory-root .memory
# Output includes "last_updated_at" field for each session.
```

## 5) Watch session (TUI output)

Render a session with ANSI colors and markdown. Omit `--session-id` to list sessions
sorted by last update time.

```bash
# List all sessions (sorted by last update)
python3 skills/vibe-coding-discussion/scripts/watch_session.py --memory-root .memory

# Watch a specific session (show all events)
python3 skills/vibe-coding-discussion/scripts/watch_session.py \
  --memory-root .memory \
  --session-id 20260220-103527-openclaw-coding-agent

# Show only last 10 events
python3 skills/vibe-coding-discussion/scripts/watch_session.py \
  --memory-root .memory \
  --session-id 20260220-103527-openclaw-coding-agent \
  --tail 10

# Follow mode: print new events as they arrive (Ctrl-C to quit)
python3 skills/vibe-coding-discussion/scripts/watch_session.py \
  --memory-root .memory \
  --session-id 20260220-103527-openclaw-coding-agent \
  --follow

# Follow mode starting from a specific index
python3 skills/vibe-coding-discussion/scripts/watch_session.py \
  --memory-root .memory \
  --session-id 20260220-103527-openclaw-coding-agent \
  --since-index 5 \
  --follow \
  --interval 2.0
```

## JSONL Event Schema

Each line in `session.jsonl` is one event:

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

Fields:
- `index`: strictly increasing integer in this session.
- `timestamp`: UTC RFC3339.
- `role`: one of `user`, `agent`, `system`.
- `message_type`: recommended values `comment`, `question`, `decision`, `summary`.
- `reply_to_index`: optional cross-reference.
