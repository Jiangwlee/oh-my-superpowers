---
task: 01
story: auth-sync
status: pending
wave: 1
depends_on: []
files_modified: [
  "src/server/infra/auth-sync-types.ts",
  "src/server/infra/auth-writers/pi.ts",
  "src/server/infra/auth-writers/__tests__/pi.test.ts"
]
---

# Task: 类型定义 + Pi 写入适配器

## Context

Story: `./stories/auth-sync/story.md`
Design: `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md`

Auth sync 需要统一的类型定义（auth-config schema）和第一个写入适配器。Pi 适配器将 auth-config 格式的凭据转换为 Pi 原生的 `~/.pi/agent/auth.json` 格式。

## Objective

**Do:**
- 定义 `AuthCredential`、`AuthModel`、`AuthConfig` TypeScript 类型
- 实现 `writePiAuth(credentials, targetPath)` 函数
- OAuth credential (`github-copilot`) 转换为 `{ type: "oauth", refresh: "<key>", access: "", expires: 0 }`
- API key credential (`kimi-coding`, `litellm`) 转换为 `{ type: "api_key", key: "<key>" }`
- 写入文件权限 `0600`，目录权限 `0700`
- TDD：先写测试再实现

**Do NOT:**
- 不实现 AuthSyncService（Task 04）
- 不实现其他 writer（Task 02/03）
- 不修改现有文件

## Read First

- `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md` — 完整设计文档，重点阅读"数据契约"和"Pi 适配器"章节
- `src/server/infra/env.ts` — 现有 infra 代码风格参考
- `src/server/infra/mindora-home.ts` — 现有 infra 代码风格参考

## File Scope

- `src/server/infra/auth-sync-types.ts` — 新增：类型定义
- `src/server/infra/auth-writers/pi.ts` — 新增：Pi writer
- `src/server/infra/auth-writers/__tests__/pi.test.ts` — 新增：Pi writer 测试

## Workflow

1. 阅读 Read First 文件，理解数据契约和代码风格
2. 定义 auth-sync-types.ts 中的类型
3. 写 Pi writer 测试（TDD Red）：
   - github-copilot oauth → Pi oauth 格式
   - kimi-coding api_key → Pi api_key 格式
   - 文件权限 0600
   - 目标目录不存在时创建
4. 实现 Pi writer（TDD Green）
5. 运行测试确认通过

## Worker Refs

- `.claude/skills/coding-orchestrator/references/constitution.md`
- `.claude/skills/coding-orchestrator/worker-refs/worker-guideline.md`

## References

- `docs/research/0006-auth-sync-mechanism-research-2026-04-12.md` — Pi auth.json 格式详情

## Deviation Rules

🟢 **Auto-fix**: Missing imports, typo fixes
🟡 **Auto-add**: Edge case test（如空 credentials 对象）
🟠 **Auto-fix blocking**: TypeScript 编译错误
🔴 **Ask orchestrator**: 修改公共类型接口、添加新依赖、触碰 File Scope 外的文件

## IRON LAW

Follow `references/constitution.md`:
- Think Before Coding → Simplicity First → Surgical Changes → Goal-Driven

**Task-specific constraints:**
- 文件头部前 20 行必须包含 YAML 格式的 purpose 和 interfaces 描述（Zero-Context Entry）
- 不使用 class，纯函数即可

## Acceptance Criteria

### Must-Haves

**Truths:**
- "给定 github-copilot oauth credential，writePiAuth 输出包含 `type: oauth`, `refresh: <key>`, `access: \"\"`, `expires: 0`"
- "给定 kimi-coding api_key credential，writePiAuth 输出包含 `type: api_key`, `key: <key>`"
- "写入文件权限为 0600"

**Artifacts:**
- path: `src/server/infra/auth-sync-types.ts`
  provides: "AuthCredential, AuthModel, AuthConfig 类型定义"
  contains: "export interface AuthConfig"
- path: `src/server/infra/auth-writers/pi.ts`
  provides: "Pi auth.json 写入函数"
  contains: "export function writePiAuth"
- path: `src/server/infra/auth-writers/__tests__/pi.test.ts`
  provides: "Pi writer 单元测试"
  contains: "writePiAuth"

**Key Links:**
- from: `src/server/infra/auth-writers/pi.ts`
  to: `src/server/infra/auth-sync-types.ts`
  pattern: `import.*from.*auth-sync-types`

## Test Plan

- [ ] `pnpm vitest run src/server/infra/auth-writers/__tests__/pi.test.ts` — Pi writer 测试通过
- [ ] `pnpm tsc --noEmit` — TypeScript 编译无错误

## Progress

- [ ] Execute — worker assigned: pending
- [ ] Review — reviewer: pending
- [ ] Test — result: pending
- [ ] Acceptance — verified: pending
