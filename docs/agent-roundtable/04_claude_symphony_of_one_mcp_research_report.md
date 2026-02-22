# claude-symphony-of-one-mcp 研究报告

## 1. 项目定位

`claude-symphony-of-one-mcp` 提供了一个中心 Hub（Express + Socket.IO + SQLite）和 MCP 工具层，用于让多个 Claude 实例进入同一房间协作。

它是本次样本中最接近“可见群聊房间”形态的项目。

## 2. 关键机制证据

### 2.1 中心 Hub + 房间模型
- `server.js:13` Express + HTTP + Socket.IO
- `server.js:53` SQLite 持久化
- `server.js:58` 内存结构：rooms/agents/messages/tasks/agentMemory
- `server.js:83` 建表：rooms/agents/messages/tasks/agent_memory/notifications

结论：具备中心化房间、成员、消息、任务、记忆全套数据模型。

### 2.2 消息广播与 @mention 通知
- `server.js:178` 解析 `@agent`
- `server.js:191` mention 生成通知并可实时推送
- `server.js:427` `/api/send` 写消息并房间广播
- `server.js:491` `/api/messages/:room` 历史查询
- `server.js:590` `/api/broadcast/:room` 系统广播

结论：天然支持“群组可见 + 定向提醒”。

### 2.3 MCP 工具映射（给 Agent 使用）
- `mcp-server.js:120` `room_join`
- `mcp-server.js:237` `send_message`
- `mcp-server.js:293` `get_messages`
- `mcp-server.js:414` `create_task`
- `mcp-server.js:473` `get_tasks`
- `mcp-server.js:533` `memory_store`
- `mcp-server.js:588` `memory_retrieve`

结论：把房间协作能力暴露成 MCP 工具，代理可直接调用。

### 2.4 共享文件工作区
- `mcp-server.js:646` `file_read`
- `mcp-server.js:699` `file_write`
- `mcp-server.js:750` `file_list`
- `server.js:240` 文件 watcher 变更广播

结论：支持“讨论 + 共享工件”同域协作。

## 3. 与目标场景的契合点

1. 最接近“临时群聊房间 + 发言可见”的需求
2. 主控可广播，成员可直接互相可见
3. 消息、任务、记忆可追溯

## 4. 不足与风险

1. 该实现主要围绕 Claude MCP 生态，异构 CLI（opencode）需额外桥接
2. 中心 Hub 增加运维复杂度（服务进程 + DB + 可用性）
3. 项目中有使用宽权限运行模式的倾向，需补安全边界

## 5. 可借鉴路线（对 skill 实现）

最值得借鉴的是“房间抽象”与“消息结构”：
- room（讨论域）
- agent（参与者）
- message（含 mention/type/timestamp）
- task（待办与收敛动作）

对 `skills/vibe-coding-discussion/` 的启发：
- 可先做无服务化简化版（本地文件消息总线），保留房间语义
- 若后续要升级实时协作，再考虑轻量 Hub 化
