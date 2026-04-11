---
task: 01
story: backend-logger
status: pending
wave: 1
depends_on: []
files_modified:
  - src/lib/infra/logger.ts
  - src/instrumentation.ts
  - package.json
  - tests/unit/lib/infra/logger.test.ts
---

# Task: 实现 Pino Logger 模块

## Context

Story: `./stories/backend-logger/story.md`
Design: `docs/refactoring/0011-backend-architecture-layering-2026-04-11.md` §6.7

mindora-ui 后端当前没有结构化日志，所有调试依赖 console.log。需要引入 Pino 作为日志库，采用 pi-server 验证过的 Singleton + Proxy 延迟初始化模式。

## Objective

**Do:**
- 安装 `pino` 和 `pino-pretty` (devDependencies)
- 创建 `src/lib/infra/logger.ts`：Singleton + Proxy 延迟初始化，导出 `logger`, `initLogger`, `parseLogLevel`, `parseLogFormat`
- 创建 `src/instrumentation.ts`（Next.js instrumentation hook）在服务端启动时调用 `initLogger`
- 编写单元测试验证 logger 初始化和级别过滤

**Do NOT:**
- 不在任何现有文件中插入日志调用（Task 02 的工作）
- 不修改 next.config.ts（Next.js 自动检测 instrumentation.ts）
- 不创建前端 logger

## Read First

- `~/Projects/pi-server/packages/server/src/logger.ts` — 参考实现（Singleton + Proxy 模式）
- `src/lib/infra/env.ts` — 了解现有环境变量加载模式
- `docs/refactoring/0011-backend-architecture-layering-2026-04-11.md:470-488` — 日志体系设计规范

## File Scope

- `src/lib/infra/logger.ts` — 新建，Logger 模块
- `src/instrumentation.ts` — 新建，Next.js instrumentation hook
- `package.json` — 添加 pino, pino-pretty 依赖
- `tests/unit/lib/infra/logger.test.ts` — 新建，单元测试

## Workflow

1. 读取 Read First 中的参考实现，理解 Proxy 模式
2. 使用 pnpm 安装 pino + pino-pretty（pino-pretty 作为 devDependencies）
3. 实现 `src/lib/infra/logger.ts`：
   - `initLogger(level, format)` — 创建/替换底层 pino 实例
   - `logger` — Proxy 对象，所有模块 import 同一个引用
   - `parseLogLevel(input)` / `parseLogFormat(input)` — 安全解析环境变量
   - 类型导出：`LogLevel`, `LogFormat`, `Logger`
4. 实现 `src/instrumentation.ts`：
   - Next.js instrumentation hook，`export async function register()` 中读 `LOG_LEVEL` + `LOG_FORMAT` 环境变量并调用 `initLogger`
   - 仅在 `process.env.NEXT_RUNTIME === 'nodejs'` 时初始化（排除 edge runtime）
5. 编写单元测试：
   - `initLogger` 后 `logger.level` 正确
   - `parseLogLevel` 对无效输入返回 `'info'`
   - `parseLogFormat` 对无效输入返回 `'json'`
   - Proxy 在 `initLogger` 前后行为一致（调用不报错）

## Worker Refs

- `.claude/skills/coding-orchestrator/references/constitution.md` — 编码准则（必读）
- `.claude/skills/coding-orchestrator/worker-refs/worker-guideline.md` — Worker 行为协议

## References

- `~/Projects/pi-server/packages/server/src/logger.ts` — 完整参考实现
- Next.js instrumentation: https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation

## Deviation Rules

🟢 **Auto-fix**:
- pino 类型导入调整
- 测试文件结构

🟡 **Auto-add**:
- pino-pretty fallback（生产环境无 pino-pretty 时降级为 JSON）

🟠 **Auto-fix blocking**:
- TypeScript 编译错误

🔴 **Ask orchestrator**:
- 修改 next.config.ts
- 引入除 pino/pino-pretty 之外的依赖
- 修改 env.ts 或其他现有文件

## IRON LAW

Follow `references/constitution.md`:
- Think Before Coding -> Simplicity First -> Surgical Changes -> Goal-Driven

**Task-specific constraints:**
- Logger 模块必须是 pi-server 模式的忠实复刻，不要发明新模式
- YAML header 必须写在 logger.ts 文件前 20 行
- 测试使用 vitest（项目已有配置）

## Acceptance Criteria

### Must-Haves

**Truths:**
- `initLogger('debug', 'plain')` 后，`logger.level === 'debug'`
- `initLogger` 前调用 `logger.info('test')` 不抛错（silent 模式）
- `parseLogLevel('invalid')` 返回 `'info'`
- `parseLogFormat(undefined)` 返回 `'json'`

**Artifacts:**
- path: `src/lib/infra/logger.ts`
  provides: "Pino singleton logger with Proxy delayed init"
  contains: `export const logger`
- path: `src/instrumentation.ts`
  provides: "Next.js server startup logger initialization"
  contains: `initLogger`
- path: `tests/unit/lib/infra/logger.test.ts`
  provides: "Logger unit tests"
  contains: `describe.*logger`

**Key Links:**
- from: `src/instrumentation.ts`
  to: `src/lib/infra/logger.ts`
  pattern: `import.*from.*lib/infra/logger`

## Test Plan

- [ ] `pnpm vitest run tests/unit/lib/infra/logger.test.ts` — 单元测试全绿
- [ ] `pnpm build` — 构建通过（instrumentation.ts 被 Next.js 正确识别）

## Progress

- [ ] Execute — worker assigned: pending
- [ ] Review — reviewer: pending
- [ ] Test — result: pending
- [ ] Acceptance — verified: pending
