---
task: 04
story: auth-sync
status: pending
wave: 2
depends_on: ["01", "02", "03"]
files_modified: [
  "src/server/infra/auth-sync.ts",
  "src/server/infra/__tests__/auth-sync.test.ts",
  "src/server/infra/env.ts",
  "src/app/api/agents/models/route.ts",
  "src/core/registry.ts"
]
---

# Task: AuthSyncService 核心 + Model API 重写 + 启动集成

## Context

Story: `./stories/auth-sync/story.md`
Design: `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md`

这是核心集成任务。AuthSyncService 是 globalThis 单例，启动时 fail-closed 拉取 auth server，之后每 30s 轮询。拉取到的 credentials 通过 Task 01-03 的 writer 写入各 provider 配置。Model 白名单缓存在内存中，替代当前有 bug 的 `listModels()` 调用。

## Objective

**Do:**
- 实现 `AuthSyncService`：`start()` / `stop()` / `pull()` / `sync()` / `getModels()` / `getCredentials()`
- `start()`: fail-closed 首次拉取 + 启动 30s interval
- `sync()`: pull → JSON diff → 有变化时调用三个 writer
- `pull()`: HTTP GET auth server + schema validation
- env.ts 新增 `AUTH_SERVER_URL` / `AUTH_SERVER_TOKEN` 读取
- 重写 `GET /api/agents/models` 从 `AuthSyncService.getModels()` 读取
- registry.ts 启动时初始化 AuthSyncService（AUTH_SERVER_URL 未配置时跳过）
- TDD

**Do NOT:**
- 不重写三个 writer（已在 Task 01-03 完成）
- 不修改 Agent 编辑器 UI（后续 story）
- 不实现 pi-server auth server 升级（独立项目）

## Read First

- `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md` — "AuthSyncService 核心"和"Model 列表"章节
- `src/core/registry.ts` — 当前 AgentRegistry 单例模式
- `src/app/api/agents/models/route.ts` — 当前 model API（将被重写）
- `src/server/infra/env.ts` — 当前环境变量加载
- `src/server/infra/auth-sync-types.ts` — 类型定义（Task 01 产出）
- `src/server/infra/auth-writers/pi.ts` — Pi writer（Task 01 产出）
- `src/server/infra/auth-writers/openclaw.ts` — OpenClaw writer（Task 02 产出）
- `src/server/infra/auth-writers/hermes.ts` — Hermes writer（Task 03 产出）

## File Scope

- `src/server/infra/auth-sync.ts` — 新增：AuthSyncService
- `src/server/infra/__tests__/auth-sync.test.ts` — 新增：集成测试
- `src/server/infra/env.ts` — 修改：新增 auth server 配置
- `src/app/api/agents/models/route.ts` — 修改：重写为白名单模式
- `src/core/registry.ts` — 修改：启动集成

## Workflow

1. 阅读 Read First，理解当前单例模式和 model API
2. 在 env.ts 中新增 AUTH_SERVER_URL / AUTH_SERVER_TOKEN
3. 写 AuthSyncService 测试：
   - pull(): mock HTTP → 验证返回 AuthConfig
   - pull(): HTTP 失败 → 抛出
   - sync(): credentials 变化 → 调用 writer
   - sync(): credentials 未变 → 不调用 writer
   - start(): fail-closed
4. 实现 AuthSyncService
5. 重写 models/route.ts
6. 修改 registry.ts 集成
7. 全部测试通过

## Worker Refs

- `.claude/skills/coding-orchestrator/references/constitution.md`
- `.claude/skills/coding-orchestrator/worker-refs/worker-guideline.md`
- `.claude/skills/coding-orchestrator/worker-refs/debugging-guideline.md`

## References

- `src/server/infra/openclaw-config.ts` — listOpenClawAgents() 可用于发现 agent 目录

## Deviation Rules

🟢 **Auto-fix**: Missing imports, typo fixes
🟡 **Auto-add**: 错误处理（HTTP 超时、JSON 解析失败），额外测试
🟠 **Auto-fix blocking**: 类型不匹配、编译错误
🔴 **Ask orchestrator**: 修改 AgentManager 接口、修改 writer 函数签名、添加新依赖

## IRON LAW

Follow `references/constitution.md`:
- Think Before Coding → Simplicity First → Surgical Changes → Goal-Driven

**Task-specific constraints:**
- AuthSyncService 使用 globalThis 单例模式（同 AgentRegistry）
- diff 逻辑用 `JSON.stringify` 比较，不要引入 deep-equal 库
- `AUTH_SERVER_URL` 未配置时，`getAuthSyncService()` 返回 null，所有调用方 null-check
- models/route.ts 中 `?provider=xxx` 过滤保留

## Acceptance Criteria

### Must-Haves

**Truths:**
- "AuthSyncService.start() 在 HTTP 失败时抛出错误（fail-closed）"
- "AuthSyncService.sync() 在 credentials 变化时调用三个 writer"
- "AuthSyncService.getModels() 返回 auth server 的模型白名单"
- "GET /api/agents/models 返回白名单而非 listModels() 结果"
- "AUTH_SERVER_URL 未配置时，Mindora UI 正常启动（跳过 auth sync）"

**Artifacts:**
- path: `src/server/infra/auth-sync.ts`
  provides: "AuthSyncService 核心"
  contains: "export function getAuthSyncService"
- path: `src/server/infra/__tests__/auth-sync.test.ts`
  provides: "AuthSyncService 测试"
  contains: "AuthSyncService"

**Key Links:**
- from: `src/server/infra/auth-sync.ts`
  to: `src/server/infra/auth-writers/pi.ts`
  pattern: `import.*writePiAuth`
- from: `src/core/registry.ts`
  to: `src/server/infra/auth-sync.ts`
  pattern: `import.*auth-sync`
- from: `src/app/api/agents/models/route.ts`
  to: `src/server/infra/auth-sync.ts`
  pattern: `import.*auth-sync`

## Test Plan

- [ ] `pnpm vitest run src/server/infra/__tests__/auth-sync.test.ts` — AuthSyncService 测试通过
- [ ] `pnpm tsc --noEmit` — 编译无错误
- [ ] `pnpm next build` — 构建成功（验证 route.ts 改动无破坏）

## Progress

- [ ] Execute — worker assigned: pending
- [ ] Review — reviewer: pending
- [ ] Test — result: pending
- [ ] Acceptance — verified: pending
