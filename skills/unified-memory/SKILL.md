---
name: unified-memory
description: >-
  Project-level long-term memory for stable preferences, repo rules, and coding constraints.
  Use when (1) users ask to remember preferences or rules across sessions ("请记住…", "记住这个",
  "下次别忘了") (2) users ask about their identity, past preferences, project rules, or
  deployment habits ("我是谁", "项目规则", "我的偏好", "部署习惯") (3) users ask to list/search
  saved memory topics (4) session is compacting or ending and durable information should be captured.
metadata:
  author: mindora
  version: 0.1.0
---

# Unified Memory

Project-level long-term memory stored in `.memory/` under the project root.

Convention: try `python3` first; if unavailable, use `python`. All commands below show `python3` only.

## Read/Write Timing (Core Rule)

| Moment | Action | Command |
|---|---|---|
| User says "请记住..." | Restate, then write | `add --topic <t> --content "<text>" --source explicit_user_memory` |
| User asks identity/preferences/rules | Read first, then answer | `autoload-topics` then `show <topic>` |
| Session compacting | Extract durable info, write | `add ... --source precompact_summary` |
| Session ending | Extract durable info, write | `add ... --source session_end_summary` |
| General coding question | Do NOT read memory | -- |

## What to Write (and What Not to Write)

Write only:

1. Stable user preferences (code style, collaboration, output format)
2. Repo/workflow rules that should persist (deployment, testing, conventions)
3. Repeatedly mentioned constraints (same rule corrected 2+ times)
4. Explicit "请记住..." requests

NO memory write WITHOUT confirming the content is non-sensitive FIRST.

Never write:

1. Secrets / tokens / credentials / private keys / cookies
2. One-off temporary decisions or task progress
3. Raw logs, stack traces, or noisy error output
4. Unconfirmed speculation

## Commands

All commands use relative path. The CLI auto-creates `.memory/` on first write.

```bash
# List topics
python3 scripts/memory_cli.py --project-dir "$PWD" topics

# Autoload top-20 topics (names only, no content)
python3 scripts/memory_cli.py --project-dir "$PWD" autoload-topics --limit 20

# Show a topic's memories
python3 scripts/memory_cli.py --project-dir "$PWD" show <topic>

# Search by keyword
python3 scripts/memory_cli.py --project-dir "$PWD" search "<query>"

# Add a memory
python3 scripts/memory_cli.py --project-dir "$PWD" add --topic <topic> --content "<text>" --source <source>

# Delete / prune / rebuild index
python3 scripts/memory_cli.py --project-dir "$PWD" delete <id>
python3 scripts/memory_cli.py --project-dir "$PWD" prune --max-items 200
python3 scripts/memory_cli.py --project-dir "$PWD" rebuild-index
```

Flags: `--json` for machine-readable output. `show` accepts `--topic <t>` or `--id <id>` or positional target.

## Fast Path by Intent

### 1. User says "请记住..."

1. Restate what will be remembered
2. `add --topic <topic> --content "<text>" --source explicit_user_memory`

### 2. User asks identity/preferences/project rules

1. `autoload-topics --limit 20`
2. Pick likely topic(s) from the list
3. `show <topic>` (or `search "<query>"` if topic unknown)
4. Answer using retrieved memory

### 3. Session compacting / exiting

1. Review the session for durable preferences, rules, and confirmed decisions
2. For each item: `add --topic <topic> --content "<text>" --source precompact_summary`
3. Prefer a few high-quality memories over many noisy ones

### 4. General coding question (not user/project-specific)

Do not read memory by default.

## Examples

### Example 1: Explicit remember

User: "请记住：我喜欢用 Google 风格 docstring"

Actions:
1. Restate: "我将记住：你偏好 Google 风格 docstring"
2. `python3 scripts/memory_cli.py --project-dir "$PWD" add --topic coding_preferences --content "用户偏好 Google 风格 docstring" --source explicit_user_memory`

Result: Memory saved. Future sessions will recall this preference.

### Example 2: Read before answering

User: "这个项目的部署规则是什么？"

Actions:
1. `python3 scripts/memory_cli.py --project-dir "$PWD" autoload-topics --limit 20`
2. Output shows `deployment_rules` topic exists
3. `python3 scripts/memory_cli.py --project-dir "$PWD" show deployment_rules`
4. Answer using retrieved content

Result: Answer grounded in saved project rules, not guessing.

## `/mem-autoload` Convention

1. Call `autoload-topics --limit 20`
2. Inject only returned topic names into context (not content)
3. When a topic becomes relevant, fetch details via `show` or `search`

## Platform Notes

This skill does not auto-install platform slash commands. Map `/mem-autoload` to the backend command per your platform:

- **Claude Code**: prefer hooks or manual execution
- **OpenCode**: use `.opencode/commands/*.md` command files
- **Codex**: use shell alias or wrapper script

## Guardrails

1. Before deployment/style/testing decisions, run `search` for relevant memories.
2. Before `add`, briefly restate what will be remembered to the user.
3. Keep topics in `lower_snake_case`, concise and descriptive.
4. On compact/exit, save only durable memories; never dump raw session summaries.
5. Prefer `show <topic>` over `search` when topic is known.
6. Do not guess unsupported CLI flags; run `--help` if unsure.

## Troubleshooting

### `.memory/` does not exist

Normal on first use. The CLI auto-creates it on first write or `rebuild-index`.

### `add` rejected with "sensitive content"

The CLI detected a token/key/cookie pattern. Rewrite as a non-sensitive summary and retry.

### `show <topic>` returns nothing

Run `topics` to list all available topics. The topic name may differ from what you expect.

### `autoload-topics` returns empty

No active memories exist yet. Write at least one memory first via `add`.
