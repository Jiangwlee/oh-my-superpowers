---
name: vibe-coding-discussion
description: >
  Use when coordinating multiple coding agents (claude-code, codex, opencode) to discuss,
  brainstorm, or review a project topic and converge on a plan — with durable session logs.
  Trigger keywords: vibe session, multi-agent discussion, 多agent讨论, 协作讨论,
  开会话, 新建讨论, 查看会话, 会话列表, watch session, list sessions,
  append message, 记录发言, 增量读取.
---

# Vibe Coding Discussion

## When to Use

直接触发（以下任一即可）：
- 用户提到 "vibe session" / "vibe coding discussion"
- 用户要求多个 agent 一起讨论、评审或头脑风暴某个话题
- 用户说"开一个会话"、"新建讨论"、"查看会话列表"、"监听会话"
- 用户执行 `init_session` / `append_message` / `read_updates` / `list_sessions` / `watch_session`
- 任何涉及把多 agent 发言写入 JSONL 日志的场景

## Overview

这个 skill 用于组织多个 coding agent 围绕一个话题协作讨论，并把全过程写入可增量读取的会话日志，避免每次全量回读上下文。

## Principles

1. 每个具体话题必须单独创建一个 session。
2. 所有发言（user + agents）必须 append 到 session JSONL。
3. agent 读取会话时优先增量拉取（从上次 index 之后）。
4. 讨论结束后必须输出“收敛方案”并记录到 session。

## Directory Layout

```text
.memory/vibe-coding-discussion/
  sessions/
    <session-id>/
      meta.json
      background.md
      session.jsonl
      cursors/
        codex.cursor
        claude-code.cursor
        opencode.cursor
```

## Workflow

1. 初始化会话（topic + 背景 + 参与者）：

```bash
python3 {SKILL_DIR}/scripts/init_session.py \
  --memory-root .memory \
  --topic "讨论支付网关重构方案" \
  --participants user,codex,claude-code,opencode \
  --background-file ./discussion.md
```

说明：
- 传入 `--background` 或 `--background-file` 后，会自动保存为 `background.md` 到 session 目录，所有参与者共享同一背景快照。

2. 写入发言（每次一条）：

```bash
python3 {SKILL_DIR}/scripts/append_message.py \
  --memory-root .memory \
  --session-id <session-id> \
  --speaker codex \
  --role agent \
  --message "建议先拆分 adapter 层，再迁移路由。"
```

3. 增量读取更新（只读上次游标之后）：

```bash
python3 {SKILL_DIR}/scripts/read_updates.py \
  --memory-root .memory \
  --session-id <session-id> \
  --consumer codex \
  --save-cursor
```

4. 讨论收敛后写入最终方案（建议 `message_type=decision`），并同步给所有 agent。

5. 查看会话列表（按最后更新时间排序）或监听会话实时动态：

```bash
# 列出所有会话（TUI 样式，按最后更新排序）
python3 {SKILL_DIR}/scripts/watch_session.py --memory-root .memory

# 渲染某个会话的全量内容
python3 {SKILL_DIR}/scripts/watch_session.py \
  --memory-root .memory \
  --session-id <session-id>

# 实时监听新消息（Ctrl-C 退出）
python3 {SKILL_DIR}/scripts/watch_session.py \
  --memory-root .memory \
  --session-id <session-id> \
  --follow
```

## References

- 命令说明与 JSONL schema: `references/commands.md`
- 脚本入口: `scripts/*.py`
