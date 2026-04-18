---
task: 02
story: auth-sync
status: pending
wave: 1
depends_on: []
files_modified: [
  "src/server/infra/auth-writers/openclaw.ts",
  "src/server/infra/auth-writers/__tests__/openclaw.test.ts"
]
---

# Task: OpenClaw 写入适配器

## Context

Story: `./stories/auth-sync/story.md`
Design: `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md`

OpenClaw 有两层配置需要写入：(1) per-agent 的 `auth-profiles.json`（凭据），(2) 全局的 `openclaw.json`（仅 litellm 等非内置 provider 的 baseUrl + model 列表）。

## Objective

**Do:**
- 实现 `writeOpenClawAuthProfiles(credentials, agentDirs)` — 遍历所有 agent 目录写入 auth-profiles.json
- 实现 `writeOpenClawModelsConfig(credentials, models, configPath)` — 写入 openclaw.json 的 models.providers（仅非内置 provider）
- auth-profiles.json 写入时保留已有 `usageStats` / `lastGood` 字段（merge，非全量覆写）
- openclaw.json 写入时只修改 `models.providers` 中的非内置 provider，不触碰其他配置
- Profile ID 格式：`<provider>:default`
- TDD

**Do NOT:**
- 不重新定义类型（从 auth-sync-types.ts import）
- 不实现发现 agent 目录的逻辑（调用方传入 agentDirs 参数）
- 不触碰 openclaw.json 中 litellm 以外的 provider 配置

## Read First

- `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md` — "OpenClaw 适配器"章节
- `src/server/infra/openclaw-config.ts` — 现有 OpenClaw 配置读取逻辑
- `src/server/infra/auth-sync-types.ts` — 类型定义（Task 01 产出，若未完成则自行定义临时类型）

## File Scope

- `src/server/infra/auth-writers/openclaw.ts` — 新增
- `src/server/infra/auth-writers/__tests__/openclaw.test.ts` — 新增

## Workflow

1. 阅读 Read First，理解 OpenClaw 的 auth-profiles.json 和 openclaw.json 格式
2. 写 auth-profiles.json writer 测试：
   - github-copilot → `{ type: "token", provider: "github-copilot", token: "<key>" }`
   - kimi-coding → `{ type: "api_key", provider: "kimi-coding", key: "<key>" }`
   - 保留已有 usageStats/lastGood
   - 多 agent 目录遍历
3. 写 openclaw.json writer 测试：
   - litellm（含 baseUrl）→ 写入 models.providers.litellm
   - 不覆盖其他 provider
   - configPath 不存在时跳过
4. 实现两个 writer
5. 测试通过

## Worker Refs

- `.claude/skills/coding-orchestrator/references/constitution.md`
- `.claude/skills/coding-orchestrator/worker-refs/worker-guideline.md`

## References

- `docs/research/0006-auth-sync-mechanism-research-2026-04-12.md` — OpenClaw auth 格式详情

## Deviation Rules

🟢 **Auto-fix**: Missing imports, typo fixes
🟡 **Auto-add**: Edge case test（如空 agentDirs 数组、openclaw.json 不存在）
🟠 **Auto-fix blocking**: TypeScript 编译错误
🔴 **Ask orchestrator**: 修改 openclaw-config.ts、添加新依赖、修改 auth-sync-types.ts

## IRON LAW

Follow `references/constitution.md`:
- Think Before Coding → Simplicity First → Surgical Changes → Goal-Driven

**Task-specific constraints:**
- 文件头部前 20 行 YAML 描述
- 纯函数，不使用 class
- 内置 provider 列表硬编码：`["github-copilot", "kimi-coding", "anthropic", "openai"]`，只有不在列表中的 provider 才写入 openclaw.json models.providers

## Acceptance Criteria

### Must-Haves

**Truths:**
- "给定 github-copilot credential + 2 个 agent 目录，两个目录的 auth-profiles.json 都写入了 `github-copilot:default` profile"
- "给定 litellm credential（含 baseUrl），openclaw.json 的 models.providers.litellm 被写入"
- "openclaw.json 中已有的其他 provider 配置不被修改"
- "auth-profiles.json 中已有的 usageStats 被保留"

**Artifacts:**
- path: `src/server/infra/auth-writers/openclaw.ts`
  provides: "OpenClaw auth-profiles.json + openclaw.json 写入"
  contains: "export function writeOpenClawAuthProfiles"
- path: `src/server/infra/auth-writers/__tests__/openclaw.test.ts`
  provides: "OpenClaw writer 单元测试"
  contains: "writeOpenClawAuthProfiles"

## Test Plan

- [ ] `pnpm vitest run src/server/infra/auth-writers/__tests__/openclaw.test.ts` — 测试通过
- [ ] `pnpm tsc --noEmit` — 编译无错误

## Progress

- [ ] Execute — worker assigned: pending
- [ ] Review — reviewer: pending
- [ ] Test — result: pending
- [ ] Acceptance — verified: pending
