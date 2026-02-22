# vibe-coding-discussion v2 设计文档：自组织群组讨论

**版本**: 2.0
**日期**: 2026-02-22
**来源**: 三方讨论会话 `20260222-042257-discussion`（claude-code / opencode / codex）

---

## 1. 背景与目标

### 1.1 当前痛点

`vibe-coding-discussion` skill 已实现会话日志（JSONL）与游标机制，但存在关键缺陷：**无法自组织**。每次发言都需要用户手动打开各工具 TUI 并输入 prompt 驱动，与"临时群组自动讨论"的目标背道而驰。

### 1.2 目标

在不引入中心化服务（无数据库、无常驻 HTTP 服务）的前提下，实现：

1. **自组织**：主控 Agent（claude-code）可一键拉起全部参与 agent，无需用户手动操作各 TUI
2. **轮次驱动**：主控按顺序向各 agent 注入本轮任务，等待响应后推进
3. **结构化日志**：所有发言以 JSONL 形式持久化，支持游标增量读取
4. **可收敛**：明确收敛条件，超限则通知用户（human checkpoint），不自动循环
5. **可复盘**：会话结束后完整日志可审计

### 1.3 设计原则

- **轻量**：只靠 Python 标准库 + tmux，无外部服务依赖
- **可插拔**：Transport 层可扩展，不锁死实现
- **向后兼容**：现有 `init_session.py / append_message.py / read_updates.py` 接口保持不变，只做增量扩展

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              orchestrate_discussion.py                   │
│         （主控状态机，P0 必做，自组织入口）                 │
│                                                          │
│  round_loop:                                             │
│    for agent in speaker_order:                           │
│      inject_round.py → tmux send-keys                   │
│      poll JSONL → wait for response                      │
│    check_convergence()                                   │
│    advance_round() or human_checkpoint()                 │
└─────────┬──────────────────────┬────────────────┬────────┘
          │                      │                │
          ▼                      ▼                ▼
   TmuxTransport          TmuxTransport     (self: claude-code)
   vcd_{sid}_opencode    vcd_{sid}_codex    直接 append_message
          │                      │
   opencode TUI            codex TUI
   (tmux session)          (tmux session)

          ▼                      ▼                ▼
   ┌──────────────────────────────────────────────────┐
   │              session.jsonl（消息总线）             │
   │         游标文件: cursors/{agent}.cursor           │
   └──────────────────────────────────────────────────┘
```

### 2.1 核心设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Transport 主路径 | TmuxTransport（P0） | claude -p 在 Claude Code 内部调用会挂起，CliRunTransport 对 claude-code 不可用 |
| claude-code 角色 | orchestrator + 直接 append_message | 无需驱动自身，直接写 JSONL |
| 消息总线 | JSONL + 游标文件 | 无服务依赖，已有实现基础 |
| 收敛策略 | 状态机 + human checkpoint | 避免无限循环，确定性可控 |
| CliRunTransport | P1 演进（opencode/codex 专用） | 已验证可行，但 claude-code 永不适用 |

### 2.2 已验证的 CliRunTransport 能力（供 P1 参考）

```bash
# opencode：--format json 输出 JSONL 事件流
opencode run --format json "prompt" 2>/dev/null \
  | python3 -c "
import sys,json
for line in sys.stdin:
    o=json.loads(line.strip())
    if o.get('type')=='text' and o.get('part',{}).get('type')=='text':
        print(o['part']['text'],end='')
"

# codex：-o 写入最后回复到文件（最干净）
codex exec -o /tmp/out.txt --color never --dangerously-bypass-approvals-and-sandbox "prompt"
cat /tmp/out.txt

# claude -p：在 Claude Code 会话内部不可用（挂起 / 报错），永远走 TmuxTransport
```

---

## 3. meta.json Schema 扩展

现有 meta.json 字段保持不变，新增以下字段：

```jsonc
{
  // === 现有字段（不变）===
  "session_id": "20260222-042257-discussion",
  "topic": "优化 vibe-coding-discussion skill",
  "participants": ["user", "claude-code", "opencode", "codex"],
  "created_at": "2026-02-22T04:22:57Z",
  "background_file": "background.md",

  // === 新增：会话状态 ===
  "status": "open",
  // 枚举：open | discussing | converging | closed

  // === 新增：轮次控制 ===
  "round": {
    "current": 0,
    "max": 5,
    "speaker_order": ["opencode", "codex", "claude-code"],
    "waiting_for": "opencode",
    // 当前等待哪个 agent 响应，null 表示本轮已全员发言
    "deadline_at": null
    // ISO8601 时间，null 表示不设超时
  },

  // === 新增：agent 注册表 ===
  "agents": {
    "claude-code": {
      "kind": "claude-code",
      "transport": "self",
      // "self" = orchestrator 自身，不需要 tmux 驱动
      "tmux_session": null,
      "state": "active",
      // 枚举：active | idle | timeout | error
      "last_seen_at": null
    },
    "opencode": {
      "kind": "opencode",
      "transport": "tmux",
      "tmux_session": "vcd_20260222-042257_opencode",
      "state": "idle",
      "last_seen_at": null
    },
    "codex": {
      "kind": "codex",
      "transport": "tmux",
      "tmux_session": "vcd_20260222-042257_codex",
      "state": "idle",
      "last_seen_at": null
    }
  },

  // === 新增：附件清单 ===
  "attachments": {
    "background_path": "background.md",
    "manifest_path": "attachments.json"
    // 可选，若存在则 orchestrator 按轮次打包上下文
  },

  // === 新增：orchestrator 配置 ===
  "orchestrator": {
    "mode": "round_robin",
    // 目前只支持 round_robin
    "auto_close": false,
    // 收敛后是否自动关闭 tmux session
    "last_run_at": null,
    "convergence_no_objection_rounds": 2
    // 连续 N 轮无 objection 则判定收敛
  }
}
```

---

## 4. 消息协议扩展

### 4.1 message_type 枚举（冻结）

| 类型 | 含义 | 发起方 |
|------|------|------|
| `session_open` | 会话初始化 | system |
| `context` | 背景/任务注入 | system |
| `kickoff` | 用户启动发言 | user |
| `comment` | 普通讨论发言 | agent |
| `proposal` | 具体方案提议 | agent |
| `objection` | 反对/质疑 | agent |
| `support` | 支持 | agent |
| `question` | 提问 | agent/user |
| `summary` | 阶段总结 | agent/system |
| `decision` | **最终决策（触发收敛）** | agent/user |
| `action` | 行动项记录 | agent |
| `heartbeat` | agent 存活心跳 | system |
| `error` | 错误记录 | system |

### 4.2 extra 字段扩展

```jsonc
{
  "extra": {
    "round": 2,                          // 当前轮次
    "addressed_to": ["codex"],           // @mention，可多值
    "attachment_refs": [                 // 引用的附件路径列表
      "docs/vibe-coding-discussion/01_devchain_research_report.md"
    ],
    "source_message_indexes": [3, 5]     // 引用前文 index，便于追踪
  }
}
```

---

## 5. 新增脚本设计

### 5.1 `spawn_agent.py` — 拉起 agent

**功能**：在 tmux 中创建独立会话，启动对应 CLI 工具，注入初始 prompt。

```
用法：
  python3 spawn_agent.py \
    --memory-root .memory \
    --session-id <session-id> \
    --agent-name opencode \
    --agent-kind opencode \
    [--initial-prompt "本次讨论..."]
```

**内部逻辑**：

```python
# 1. 生成 tmux session 名称（最长 64 字符，tmux 限制）
tmux_name = f"vcd_{session_id[:30]}_{agent_name}"

# 2. 创建 tmux session（detach 模式，不阻塞主控）
subprocess.run(["tmux", "new-session", "-d", "-s", tmux_name, "-c", work_dir])

# 3. 启动对应 CLI 工具
cli_cmds = {
    "opencode": ["opencode"],
    "codex":    ["codex"],
    "claude-code": ["claude"],
}
subprocess.run(["tmux", "send-keys", "-t", tmux_name,
                " ".join(cli_cmds[agent_kind]), "Enter"])

# 4. 等待工具就绪（轮询 pane 内容，检测 idle 提示符）
_wait_for_idle(tmux_name, timeout=30)

# 5. 注入初始 prompt（含 background 路径 + session 路径 + 首轮任务）
initial_prompt = _render_initial_prompt(session_id, agent_name, background_path, ...)
_inject_text(tmux_name, initial_prompt)

# 6. 更新 meta.json agents 表（写入 tmux_session 名称）
meta["agents"][agent_name]["tmux_session"] = tmux_name
meta["agents"][agent_name]["state"] = "active"
_save_meta(meta_path, meta)
```

**idle 检测**：

```python
def _wait_for_idle(tmux_name: str, timeout: int = 30) -> bool:
    """等待 pane 出现输入提示符（agent 已就绪）。"""
    import time
    deadline = time.time() + timeout
    # 各工具的 idle 特征（pane 内容最后一行）
    idle_patterns = ["$", ">", "claude>", "opencode>", "codex>",
                     "╭─", "❯", "✓"]
    while time.time() < deadline:
        pane_text = subprocess.check_output(
            ["tmux", "capture-pane", "-p", "-t", tmux_name]
        ).decode()
        last_line = pane_text.strip().splitlines()[-1] if pane_text.strip() else ""
        if any(p in last_line for p in idle_patterns):
            return True
        time.sleep(1)
    return False  # timeout，调用方决定是否继续
```

**初始 prompt 模板**：

```
你正在参与一个协作讨论会话。

讨论背景请阅读：
{memory_root}/vibe-coding-discussion/sessions/{session_id}/background.md

读取当前讨论历史（增量，每次只读新消息）：
python3 {skill_dir}/scripts/read_updates.py \
  --memory-root {memory_root} \
  --session-id {session_id} \
  --consumer {agent_name} \
  --save-cursor \
  --max-events 30

本轮任务：
{initial_round_prompt}

发言完毕后，执行以下命令写入你的发言：
python3 {skill_dir}/scripts/append_message.py \
  --memory-root {memory_root} \
  --session-id {session_id} \
  --speaker {agent_name} \
  --role agent \
  --message-type comment \
  --message "你的完整发言内容（一次性传入，不要分多次调用）"
```

---

### 5.2 `inject_round.py` — 注入轮次任务

**功能**：向指定 agent 的 tmux session 注入本轮 prompt，支持 busy 检测与 Ctrl+C 中断。

```
用法：
  python3 inject_round.py \
    --memory-root .memory \
    --session-id <session-id> \
    --agent-name opencode \
    --round-prompt "请阅读上一轮发言，给出你对 TransportAdapter 方案的看法" \
    [--timeout 60]
```

**内部逻辑**：

```python
# 1. 读取 meta.json，查找 tmux session 名
tmux_name = meta["agents"][agent_name]["tmux_session"]

# 2. busy 检测：若 pane 有活动输出，发 Ctrl+C 中断
if _is_busy(tmux_name):
    subprocess.run(["tmux", "send-keys", "-t", tmux_name, "C-c", ""])
    time.sleep(0.5)

# 3. 等待 idle（最多 timeout 秒）
if not _wait_for_idle(tmux_name, timeout=args.timeout):
    logger.warning("agent %s 未在 %ds 内进入 idle，强制注入", agent_name, args.timeout)

# 4. 构造本轮 prompt（含 read_updates 命令 + 任务说明 + append_message 模板）
prompt = _render_round_prompt(session_id, agent_name, round_number, args.round_prompt, ...)

# 5. 注入
_inject_text(tmux_name, prompt)

# 6. 更新 meta.json：waiting_for = agent_name，state = active
```

**busy 检测**：

```python
def _is_busy(tmux_name: str) -> bool:
    """检测 pane 是否正在输出（近 1 秒内有变化）。"""
    snap1 = _capture_pane(tmux_name)
    time.sleep(1)
    snap2 = _capture_pane(tmux_name)
    return snap1 != snap2
```

---

### 5.3 `orchestrate_discussion.py` — 主控状态机

**功能**：串联完整讨论生命周期：拉起 → 逐轮注入 → 等待响应 → 收敛判定 → 关闭。这是自组织的真正入口，P0 必做。

```
用法：
  python3 orchestrate_discussion.py \
    --memory-root .memory \
    --session-id <session-id> \
    [--max-rounds 5] \
    [--round-timeout 300] \
    [--auto-spawn]
```

**主循环逻辑**：

```python
def run_discussion(session_id, max_rounds, round_timeout):
    meta = load_meta(session_id)

    # Phase 1: 拉起所有 agent（若 --auto-spawn 且尚未启动）
    if args.auto_spawn:
        for agent_name, agent_cfg in meta["agents"].items():
            if agent_cfg["transport"] == "tmux" and not _tmux_exists(agent_cfg["tmux_session"]):
                spawn_agent(session_id, agent_name, agent_cfg["kind"])

    # Phase 2: 轮次循环
    while meta["round"]["current"] < max_rounds:
        round_num = meta["round"]["current"]
        meta["status"] = "discussing"
        _save_meta(meta)

        for agent_name in meta["round"]["speaker_order"]:
            agent_cfg = meta["agents"][agent_name]

            if agent_cfg["transport"] == "self":
                # claude-code 自身发言：直接提示（不走 tmux）
                _notify_human_or_self(session_id, round_num, agent_name)
                _wait_for_self_response(session_id, agent_name, timeout=round_timeout)
            else:
                # 注入轮次任务
                inject_round(session_id, agent_name, round_prompt=_build_round_prompt(round_num))
                # 等待 JSONL 出现新消息
                _wait_for_response(session_id, agent_name, timeout=round_timeout)

        # Phase 3: 收敛检测
        result = check_convergence(session_id, meta)
        if result.converged:
            _write_summary(session_id, result.reason)
            meta["status"] = "closed"
            _save_meta(meta)
            return

        # 推进下一轮
        meta["round"]["current"] += 1
        _save_meta(meta)

    # Phase 4: 超过 round_max，human checkpoint
    _human_checkpoint(session_id, reason=f"已达最大轮次 {max_rounds}，请人工决策")
    meta["status"] = "converging"
    _save_meta(meta)
```

**收敛检测**：

```python
def check_convergence(session_id, meta) -> ConvergenceResult:
    events = read_jsonl(session_id)

    # 条件 1：出现 decision 消息
    decisions = [e for e in events if e["message_type"] == "decision"]
    if decisions:
        return ConvergenceResult(converged=True, reason="decision message found")

    # 条件 2：连续 N 轮无 objection
    n = meta["orchestrator"]["convergence_no_objection_rounds"]
    current = meta["round"]["current"]
    if current >= n:
        recent_rounds = [e for e in events
                         if e.get("extra", {}).get("round", -1) >= current - n]
        objections = [e for e in recent_rounds if e["message_type"] == "objection"]
        if not objections:
            return ConvergenceResult(converged=True, reason=f"no objection in last {n} rounds")

    return ConvergenceResult(converged=False)
```

**等待响应**：

```python
def _wait_for_response(session_id, agent_name, timeout=300) -> bool:
    """轮询 JSONL，等待 agent 写入新消息。"""
    snapshot = _count_messages(session_id, agent_name)
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = _count_messages(session_id, agent_name)
        if current > snapshot:
            return True
        time.sleep(3)
    logger.warning("agent %s 超时 %ds 未响应", agent_name, timeout)
    return False
```

---

## 6. 现有脚本增强

### 6.1 `read_updates.py`

新增参数：

| 参数 | 说明 |
|------|------|
| `--max-events N` | 最多返回 N 条事件（防止单次注入 context 过长） |
| `--since-round N` | 只返回第 N 轮及之后的消息 |

游标格式升级（向后兼容旧纯数字格式）：

```json
// 新格式（JSON）
{"last_index": 42, "last_read_at": "2026-02-22T12:31:00Z"}

// 旧格式（纯数字）仍可解析：
// 读取时：若能解析为 int，则兼容；若为 JSON，则取 last_index
```

### 6.2 `append_message.py`

新增参数：

| 参数 | 说明 |
|------|------|
| `--round N` | 记录当前轮次到 extra.round |
| `--addressed-to names` | 逗号分隔的 @mention 目标，写入 extra.addressed_to |

message_type 软验证（warning 不阻断）：

```python
KNOWN_MESSAGE_TYPES = {
    "session_open", "context", "kickoff", "comment", "proposal",
    "objection", "support", "question", "summary", "decision",
    "action", "heartbeat", "error"
}
if args.message_type not in KNOWN_MESSAGE_TYPES:
    logger.warning("未知 message_type: %s，仍允许写入", args.message_type)
```

### 6.3 `init_session.py`

扩展 meta.json 初始化，支持新增字段：

```
新增参数：
  --max-rounds N          最大轮次，默认 5
  --speaker-order names   发言顺序（逗号分隔），默认 participants 顺序（去除 user）
  --round-timeout N       单轮单 agent 超时秒数，默认 300
  --auto-close            收敛后自动 kill tmux sessions
```

---

## 7. 附件策略

### 7.1 `background.md`

会话创建时一次性快照，所有 agent 共享同一副本（现有实现，不变）。

### 7.2 `attachments.json`（P1）

机器可读的附件清单，用于 orchestrator 按轮次分发上下文（避免每轮全量灌入所有附件）：

```json
[
  {
    "path": "docs/vibe-coding-discussion/01_devchain_research_report.md",
    "title": "Devchain 研究报告",
    "category": "research",
    "required_for_rounds": [1]
  },
  {
    "path": "docs/vibe-coding-discussion/03_metaswarm_research_report.md",
    "title": "Metaswarm 研究报告",
    "category": "research",
    "required_for_rounds": [1]
  }
]
```

### 7.3 轮次上下文包（P1）

每轮生成临时文件，便于审计和重试：

```
.memory/vibe-coding-discussion/sessions/{session_id}/
  rounds/
    round-001/
      opencode-prompt.md    # 注入给 opencode 的完整上下文
      codex-prompt.md       # 注入给 codex 的完整上下文
      claude-code-prompt.md # 自组织时 claude-code 的参考上下文
```

---

## 8. 收敛协议

### 8.1 收敛条件（按优先级）

1. **decision 消息出现**：任意 agent 写入 `message_type=decision` 的消息
2. **连续 N 轮无 objection**：`orchestrator.convergence_no_objection_rounds` 配置，默认 2
3. **round >= round_max**：触发 human_checkpoint，不自动收敛

### 8.2 human_checkpoint 流程

```python
# orchestrate_discussion.py 写入 system 消息
append_message(
    speaker="system",
    message_type="heartbeat",
    message=f"已达最大轮次 {round_max}，无法自动收敛。请用户介入，执行以下命令写入决策：\n"
            f"python3 append_message.py --message-type decision --message '你的决策内容'",
    tags=["human_checkpoint"]
)
# 更新 meta status = "converging"，暂停 orchestrator
```

### 8.3 关闭流程

收敛后（自动或手动）：

```bash
python3 close_session.py \
  --session-id <session-id> \
  --summary "最终收敛方案：..." \
  [--kill-tmux]   # 可选：kill 所有相关 tmux session
```

---

## 9. 目录结构（最终）

```
.claude/skills/vibe-coding-discussion/
├── SKILL.md
├── scripts/
│   ├── common.py                   # 已有，不变
│   ├── init_session.py             # 已有，扩展 meta schema
│   ├── append_message.py           # 已有，增加 --round/--addressed-to
│   ├── read_updates.py             # 已有，增加 --max-events/--since-round + JSON cursor
│   ├── list_sessions.py            # 已有，不变
│   ├── watch_session.py            # 已有，不变
│   ├── spawn_agent.py              # 新增 P0
│   ├── inject_round.py             # 新增 P0
│   ├── orchestrate_discussion.py   # 新增 P0（主控状态机）
│   └── close_session.py            # 新增 P1
└── references/
    └── commands.md

.memory/vibe-coding-discussion/
└── sessions/
    └── {session-id}/
        ├── meta.json
        ├── background.md
        ├── attachments.json        # P1
        ├── session.jsonl
        ├── cursors/
        │   ├── claude-code.cursor
        │   ├── opencode.cursor
        │   └── codex.cursor
        └── rounds/                 # P1
            └── round-001/
                ├── opencode-prompt.md
                └── codex-prompt.md
```

---

## 10. 实现优先级

### P0（本轮实现，解决自组织核心痛点）

| 编号 | 内容 | 文件 |
|------|------|------|
| P0-1 | meta.json schema 扩展（status/round/agents/orchestrator） | `init_session.py` |
| P0-2 | spawn_agent.py（tmux 拉起 + idle 检测 + 初始 prompt 注入） | 新增 |
| P0-3 | inject_round.py（busy 检测 + Ctrl+C + 轮次注入） | 新增 |
| P0-4 | orchestrate_discussion.py（主控状态机，完整生命周期） | 新增 |
| P0-5 | read_updates.py 增强（--max-events + JSON cursor） | 修改 |
| P0-6 | append_message.py 增强（--round + message_type 校验） | 修改 |

### P1（后续演进）

| 编号 | 内容 |
|------|------|
| P1-1 | close_session.py（写 summary + kill-tmux） |
| P1-2 | attachments.json + 轮次上下文包打包 |
| P1-3 | CliRunTransport（invoke_agent.py，仅 opencode/codex） |

### P2（长期）

| 编号 | 内容 |
|------|------|
| P2-1 | MCPTransport（codex-as-mcp 等） |
| P2-2 | 多 claude-code 实例参与（需 TmuxTransport，对抗式评审） |

---

## 11. 关键约束

1. **claude -p 永不作为子进程调用**：在 Claude Code 会话内调用会挂起（已实测），claude-code 只作为 orchestrator，transport 标记为 `self`
2. **tmux 依赖**：执行前检测 `which tmux`，未安装则给出安装提示并退出
3. **session 目录权限**：建议设置 `chmod 700`，避免其他用户读取讨论内容
4. **prompt 注入字符转义**：tmux send-keys 注入文本时，特殊字符（单引号、反斜杠等）需转义
5. **禁止正则解析 JSONL**：始终用 `json.loads()`（遵循 CLAUDE.md）

---

## 12. 测试要点

```bash
# 1. 单元测试：spawn_agent（mock tmux）
python -m unittest tests/test_spawn_agent.py

# 2. 集成测试：init + spawn + inject + read_updates（需要 tmux）
python -m unittest tests/test_orchestrate_integration.py

# 3. 收敛测试：decision 消息 / 无 objection / 超轮次
python -m unittest tests/test_convergence.py
```

---

*本文档基于 2026-02-22 三方讨论会话 `20260222-042257-discussion` 的所有发言（index 0–10）综合生成。*
