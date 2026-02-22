---
name: agent-roundtable
description: Use when the user wants to start a multi-agent discussion, asks multiple agents to discuss a topic together, says "roundtable" / "agent roundtable" / "multi-agent discussion", or wants to coordinate claude-code, codex, opencode around a shared topic with durable session logs.
---

# Agent Roundtable

邀请外部 agent（codex、opencode 等）围绕一个话题协作讨论，全程写入可增量读取的会话日志（JSONL）。

**适用场景**：需要引入外部 agent 参与时。如果只是 user + claude-code 讨论，直接对话即可；引入外部 agent 前，先通过对话梳理背景，再用 `--background-file` 注入，过滤噪音。

## Hard Rules

- **禁止读 `scripts/*.py` 源码**。脚本用法见 `references/commands.md`，或运行 `python3 {SKILL_DIR}/scripts/<name>.py --help`。
- 每个 agent 只需 `spawn` 一次，但可多次 `inject`。
- `spawn_agent` 必须先于 `inject_round` 运行。
- 讨论结束必须写入 `--message-type decision` 作为收敛记录。
- **`close_session` 是必须的收尾步骤**，跳过会导致 tmux session 永久驻留。

## 工作流

```
1. init_session     → 创建 session（传入 --background-file 注入背景）
2. spawn_agent      → 为每个外部 agent 创建 tmux session（每 agent 各调用一次）
3. inject_round     → 向外部 agent 注入本轮 prompt，等待其 append 回复
4. append_message   → claude-code 自身发言
5. 重复 3-4 直至达成共识
6. append_message   --message-type decision  → 写入决策
7. close_session    → 写入 session_close 事件并 kill 所有 tmux session
```

一键运行全流程（自动 spawn + 多轮 inject + 收敛检测）：

```bash
python3 {SKILL_DIR}/scripts/orchestrate_discussion.py \
  --memory-root .memory \
  --topic "讨论话题" \
  --agents "codex:codex,opencode:opencode" \
  --max-rounds 5
```

## Script Reference

所有脚本的完整参数说明见 `references/commands.md`。

快速查看单个脚本：`python3 {SKILL_DIR}/scripts/<name>.py --help`
