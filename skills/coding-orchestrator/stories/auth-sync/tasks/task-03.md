---
task: 03
story: auth-sync
status: pending
wave: 1
depends_on: []
files_modified: [
  "src/server/infra/auth-writers/hermes.ts",
  "src/server/infra/auth-writers/__tests__/hermes.test.ts"
]
---

# Task: Hermes 写入适配器

## Context

Story: `./stories/auth-sync/story.md`
Design: `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md`

Hermes 通过 env vars 读取凭据（不持久化 token）。写入适配器需要将 credentials 转换为 .env 文件中的 key=value 格式。

## Objective

**Do:**
- 实现 `writeHermesEnv(credentials, envPath)` — 写入/更新 .env 文件
- Provider → env var 映射：`github-copilot → COPILOT_GITHUB_TOKEN`，`kimi-coding → KIMI_API_KEY`
- 保留 .env 中已有的其他变量（非 auth-sync 管理的变量）
- litellm 不写入（Hermes 不支持）
- TDD

**Do NOT:**
- 不重新定义类型（从 auth-sync-types.ts import）
- 不修改 Hermes 配置文件（config.yaml）
- 不触碰 .env 中非映射范围的变量

## Read First

- `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md` — "Hermes 适配器"章节
- `src/server/infra/auth-sync-types.ts` — 类型定义（Task 01 产出，若未完成则自行定义临时类型）

## File Scope

- `src/server/infra/auth-writers/hermes.ts` — 新增
- `src/server/infra/auth-writers/__tests__/hermes.test.ts` — 新增

## Workflow

1. 阅读 Read First
2. 写测试：
   - github-copilot → `COPILOT_GITHUB_TOKEN=<key>`
   - kimi-coding → `KIMI_API_KEY=<key>`
   - litellm → 不写入
   - 保留 .env 中已有的其他变量
   - .env 不存在时创建
3. 实现 writer
4. 测试通过

## Worker Refs

- `.claude/skills/coding-orchestrator/references/constitution.md`
- `.claude/skills/coding-orchestrator/worker-refs/worker-guideline.md`

## References

- `docs/research/0006-auth-sync-mechanism-research-2026-04-12.md` — Hermes env var 映射

## Deviation Rules

🟢 **Auto-fix**: Missing imports, typo fixes
🟡 **Auto-add**: Edge case test（如 .env 末尾无换行）
🟠 **Auto-fix blocking**: TypeScript 编译错误
🔴 **Ask orchestrator**: 添加新的 provider → env var 映射、触碰 File Scope 外的文件

## IRON LAW

Follow `references/constitution.md`:
- Think Before Coding → Simplicity First → Surgical Changes → Goal-Driven

**Task-specific constraints:**
- 文件头部前 20 行 YAML 描述
- 纯函数
- Provider → env var 映射硬编码为 const Record

## Acceptance Criteria

### Must-Haves

**Truths:**
- "给定 github-copilot credential，.env 文件包含 COPILOT_GITHUB_TOKEN=<key>"
- "给定 kimi-coding credential，.env 文件包含 KIMI_API_KEY=<key>"
- "litellm credential 不写入 .env"
- ".env 中已有的 OTHER_VAR=value 被保留"

**Artifacts:**
- path: `src/server/infra/auth-writers/hermes.ts`
  provides: "Hermes .env 写入"
  contains: "export function writeHermesEnv"
- path: `src/server/infra/auth-writers/__tests__/hermes.test.ts`
  provides: "Hermes writer 单元测试"
  contains: "writeHermesEnv"

## Test Plan

- [ ] `pnpm vitest run src/server/infra/auth-writers/__tests__/hermes.test.ts` — 测试通过
- [ ] `pnpm tsc --noEmit` — 编译无错误

## Progress

- [ ] Execute — worker assigned: pending
- [ ] Review — reviewer: pending
- [ ] Test — result: pending
- [ ] Acceptance — verified: pending
