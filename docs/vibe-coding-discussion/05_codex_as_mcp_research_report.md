# codex-as-mcp 研究报告

## 1. 项目定位

`codex-as-mcp` 是一个极简桥接器：将 Codex CLI 封装为 MCP 工具，供上层 Agent 调用。

它不是编排系统，但非常适合“把 Codex 作为可调用 subagent”。

## 2. 关键机制证据

### 2.1 工具面：单体与并行
- `src/codex_as_mcp/server.py:72` `spawn_agent`
- `src/codex_as_mcp/server.py:180` `spawn_agents_parallel`
- `README.md:121` 两个工具的用途说明

结论：并行子 agent 调用是内置能力。

### 2.2 底层执行：直接调用 Codex CLI
- `src/codex_as_mcp/server.py:106` 构造 `codex e` 命令
- `src/codex_as_mcp/server.py:111` `--dangerously-bypass-approvals-and-sandbox`
- `src/codex_as_mcp/server.py:112` `--output-last-message`
- `src/codex_as_mcp/server.py:124` `asyncio.create_subprocess_exec`

结论：满足“复用 Codex CLI 原生 agent 能力”的核心诉求。

### 2.3 并发与超时处理
- `src/codex_as_mcp/server.py:29` 默认超时 8 小时
- `src/codex_as_mcp/server.py:136` 运行中 progress heartbeat
- `src/codex_as_mcp/server.py:240` `asyncio.gather` 并行聚合
- `README.md:126` 说明客户端工具超时问题与配置

结论：长任务场景可用，但要协调 MCP 客户端超时策略。

## 3. 与目标场景的契合点

1. 非常适合作为“Claude 主控 -> Codex subagent”桥
2. 并行调用接口直接可用
3. 对上层编排保持最小侵入

## 4. 不足与风险

1. 不提供群聊语义（无 room/message protocol）
2. 返回是“任务结果”而非“持续对话流”
3. 宽权限参数默认开启，需要风险隔离

## 5. 可借鉴路线（对 skill 实现）

借鉴它作为“执行适配器”层：
- 上层负责讨论协议（轮次、发言顺序、收敛）
- 下层用 `spawn_agent/spawn_agents_parallel` 执行具体发言任务

对 `skills/vibe-coding-discussion/` 的启发：
- 可优先抽象统一适配接口：`invoke(agent, prompt, mode)`
- Codex 先落地，OpenCode/Claude 再按同接口扩展
