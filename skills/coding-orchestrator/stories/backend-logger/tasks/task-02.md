---
task: 02
story: backend-logger
status: pending
wave: 2
depends_on: ["01"]
files_modified:
  - src/lib/team/registry.ts
  - src/proxy/bridge.ts
  - src/proxy/openclaw.ts
---

# Task: 关键路径日志点注入

## Context

Story: `./stories/backend-logger/story.md`
Design: `docs/refactoring/0011-backend-architecture-layering-2026-04-11.md` §6.7

Task 01 已实现 Logger 模块。本任务在后端 3 个核心服务端模块中替换 console.log / debug flag 为结构化日志。

## Objective

**Do:**
- 在 `registry.ts` 中用 `logger.info/debug/error` 替换现有的 console.log 和 `appendTeamRenderDebugLog` 调用（关键生命周期事件）
- 在 `bridge.ts` 中添加 WS 连接/断开/错误日志
- 在 `openclaw.ts` 中添加 OpenClaw WS 连接/认证/错误日志
- 日志事件命名遵循 dot-separated 规范（如 `registry.lead_spawned`, `bridge.ws_connected`, `openclaw.auth_completed`）
- 日志包含上下文字段：teamId, sessionId, memberId（如适用）

**Do NOT:**
- 不在 API route 文件中添加日志（范围太大，后续做）
- 不在前端代码中添加日志
- 不删除 `render-debug.ts` 模块（现有 debug flag 保留，日志是额外新增）
- 不改变任何业务逻辑
- 不在高频事件（如每个 message_update delta）上加 info 级别日志，这些用 debug 级别

## Read First

- `src/lib/infra/logger.ts` — Task 01 产出的 Logger 模块
- `src/lib/team/registry.ts:1-40` — 理解现有调试机制（MINDORA_DEBUG_LEAD, MINDORA_DEBUG_TEAM_RENDER）
- `src/proxy/bridge.ts` — 完整阅读（118 行）
- `src/proxy/openclaw.ts:1-50` — 理解连接建立流程

## File Scope

- `src/lib/team/registry.ts` — 添加 logger 导入和关键日志点
- `src/proxy/bridge.ts` — 添加 logger 导入和 WS 事件日志
- `src/proxy/openclaw.ts` — 添加 logger 导入和连接/认证日志

## Workflow

1. 读取 Read First 文件，理解现有代码和调试机制
2. 在 registry.ts 中识别关键生命周期事件，添加日志：
   - `registry.lead_spawned` (info) — Lead session 创建
   - `registry.lead_ended` (info) — Lead session 结束
   - `registry.plan_intercepted` (info) — Plan 被拦截
   - `registry.run_started` (info) — Pipeline run 开始
   - `registry.run_completed` (info) — Pipeline run 完成
   - `registry.sse_client_connected` (debug) — SSE 客户端连接
   - `registry.sse_client_disconnected` (debug) — SSE 客户端断开
   - `registry.event_broadcast` (debug) — 事件广播（带 seq）
   - 错误路径用 `logger.error`
3. 在 bridge.ts 中添加：
   - `bridge.ws_connected` (info) — 浏览器 WS 连接
   - `bridge.ws_closed` (info) — 浏览器 WS 关闭
   - `bridge.upstream_error` (error) — 上游 WS 错误
4. 在 openclaw.ts 中添加：
   - `openclaw.connecting` (info) — 发起连接
   - `openclaw.auth_completed` (info) — Ed25519 认证完成
   - `openclaw.connection_error` (error) — 连接错误
5. 验证 `pnpm build` 通过

## Worker Refs

- `.claude/skills/coding-orchestrator/references/constitution.md` — 编码准则（必读）
- `.claude/skills/coding-orchestrator/worker-refs/worker-guideline.md` — Worker 行为协议

## References

- `docs/refactoring/0011-backend-architecture-layering-2026-04-11.md:470-488` — 日志规范
- `~/Projects/pi-server/packages/server/src/routes/runtime.ts` — pi-server 中 logger 使用范例

## Deviation Rules

🟢 **Auto-fix**:
- 导入路径调整
- 日志事件名微调

🟡 **Auto-add**:
- 在明显的错误处理 catch 块中添加 logger.error（即使未在上方列出）

🟠 **Auto-fix blocking**:
- TypeScript 编译错误

🔴 **Ask orchestrator**:
- 修改业务逻辑
- 删除现有的 debug flag 机制
- 添加日志到 File Scope 之外的文件

## IRON LAW

Follow `references/constitution.md`:
- Think Before Coding -> Simplicity First -> Surgical Changes -> Goal-Driven

**Task-specific constraints:**
- 只做日志插入，不改业务逻辑。每一行变更都必须是 import 或 logger 调用。
- info 级别只用于关键生命周期事件，debug 用于高频事件
- 所有日志调用的第一个参数是上下文对象 `{ teamId, sessionId, ... }`，第二个参数是事件名字符串

## Acceptance Criteria

### Must-Haves

**Truths:**
- `LOG_LEVEL=debug pnpm dev` 启动后，创建 Team session 能看到 `registry.lead_spawned` 日志
- Chat 场景连接 OpenClaw 能看到 `openclaw.connecting` 和 bridge 日志
- 不改变任何现有功能行为

**Artifacts:**
- path: `src/lib/team/registry.ts`
  provides: "Team registry with structured logging"
  contains: `import.*logger.*from.*lib/infra/logger`
- path: `src/proxy/bridge.ts`
  provides: "WS bridge with structured logging"
  contains: `logger.info`

**Key Links:**
- from: `src/lib/team/registry.ts`
  to: `src/lib/infra/logger.ts`
  pattern: `import.*logger`
- from: `src/proxy/bridge.ts`
  to: `src/lib/infra/logger.ts`
  pattern: `import.*logger`

## Test Plan

- [ ] `pnpm build` — 构建通过
- [ ] `LOG_LEVEL=info LOG_FORMAT=plain pnpm dev` — 启动输出正常
- [ ] 不存在 `console.log` 新增（grep 确认）

## Progress

- [ ] Execute — worker assigned: pending
- [ ] Review — reviewer: pending
- [ ] Test — result: pending
- [ ] Acceptance — verified: pending
