# Claude-Code-Workflow 研究报告

## 1. 项目定位

`Claude-Code-Workflow`（以下简称 CCW）是一个围绕 Claude/Codex/Gemini CLI 的工作流与会话编排系统，包含：
- CLI 工具执行层
- PTY 会话管理层
- Flow DAG 编排层
- Team 消息日志与可视化 API

它更偏“工程化编排与可观测”，不是原生聊天室。

## 2. 关键机制证据

### 2.1 Team 消息总线（JSONL 持久化）
- `ccw/src/tools/team-msg.ts:1` 定义 Team Message Bus
- `ccw/src/tools/team-msg.ts:109` 支持操作：`log/read/list/status/delete/clear`
- `ccw/src/tools/team-msg.ts:187` 新目录结构：`.workflow/.team/{session-id}/.msg/`
- `ccw/src/tools/team-msg.ts:251` `opLog` 写入结构化消息（from/to/type/summary/ref/data）
- `ccw/src/tools/team-msg.ts:297` `opList` 支持按 from/to/type + last 过滤
- `ccw/src/tools/team-msg.ts:322` `opStatus` 聚合成员活跃状态

结论：具备“消息归档 + 查询”的强基础，但不是实时广播总线。

### 2.2 Team 可观测 API
- `ccw/src/core/routes/team-routes.ts:16` 提供 `/api/teams` 系列接口
- `ccw/src/core/routes/team-routes.ts:251` 团队列表
- `ccw/src/core/routes/team-routes.ts:471` 消息查询
- `ccw/src/core/routes/team-routes.ts:498` 成员状态查询
- `ccw/src/core/routes/team-routes.ts:422` artifacts 树与内容读取

结论：可做“讨论记录面板”，支持会后复盘。

### 2.3 CLI 会话生命周期与路由注入
- `ccw/src/core/services/cli-session-manager.ts:158` `CliSessionManager`
- `ccw/src/core/services/cli-session-manager.ts:214` 创建 PTY session
- `ccw/src/core/services/cli-session-manager.ts:349` 会话退出回收
- `ccw/src/core/services/cli-session-manager.ts:415` `pauseSession`
- `ccw/src/core/services/cli-session-manager.ts:440` `resumeSession`
- `ccw/src/core/services/cli-session-manager.ts:466` `execute` 向会话注入命令

结论：非常适合做“临时群组参与者”生命周期控制。

### 2.4 Flow 节点路由到指定会话（sendToSession）
- `ccw/src/core/services/flow-executor.ts:250` `delivery=sendToSession`
- `ccw/src/core/services/flow-executor.ts:260` 通过 `cliSessionMux` 找会话并注入
- `ccw/src/core/services/flow-executor.ts:284` 调用 `manager.execute`
- `ccw/src/core/services/flow-executor.ts:329` 返回 executionId/command 作为结构化输出

结论：这给“主控按轮次点名发言”提供了直接技术支点。

## 3. 与目标场景的契合点

1. 可将 Claude/Codex/OpenCode 各自绑定为独立 PTY 会话
2. 主控可按轮次向指定会话发送 prompt（`sendToSession`）
3. 可把每轮发言写入 `team_msg`，形成可追踪会议纪要
4. 可通过 Team API 查看成员活跃度与消息轨迹

## 4. 不足与风险

1. `team_msg` 是日志型总线，不是实时 pub/sub
2. 缺省没有“群组可见消息自动分发”机制
3. 讨论收敛（共识判定）需要上层策略补齐
4. 多会话并发下顺序控制需额外加“轮次协议”

## 5. 可借鉴路线（对 skill 实现）

可借鉴“会话路由 + 持久消息”双层架构：
- 控制平面：主控按轮次 `sendToSession`
- 记录平面：所有交互结构化写入 `team_msg`

对 `skills/vibe-coding-discussion/` 的启发：
- 优先实现“可控轮询 + 结构化日志 + 可收敛总结”
- 暂不追求真正多端实时聊天室
