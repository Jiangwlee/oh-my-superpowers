# Story: auth-sync

## Goal

Mindora UI 从 pi-server auth server 定期拉取凭据和模型白名单，同步写入本地三个 Provider（Pi / OpenClaw / Hermes）的配置文件，并用白名单替代当前有 bug 的模型列表拉取。

## Context

- Design: `docs/brainstorming/specs/2026-04-12-auth-sync-mechanism-design.md`
- Research: `docs/research/0006-auth-sync-mechanism-research-2026-04-12.md`
- Related code:
  - `src/core/registry.ts` — AgentRegistry 单例，启动入口
  - `src/server/infra/env.ts` — 环境变量加载
  - `src/app/api/agents/models/route.ts` — 当前模型列表 API（有 bug，需重写）
  - `src/core/adapters/types.ts` — Provider/Model 类型定义

## Scope

**In scope:**
- AuthSyncService 核心（定期拉取 + diff + 分发）
- 三个写入适配器（Pi / OpenClaw / Hermes）
- Model 列表 API 重写（从白名单读取）
- 启动集成（registry 初始化）
- 类型定义

**Out of scope:**
- pi-server auth server 升级（Task 8，独立项目，手动完成）
- UI 层 Agent 编辑器的 model selector 改造（后续 story）
- OAuth device flow UI（Mindora UI 只消费凭据，不提供）

## Tasks

| Task | Name | Status | Spec |
|------|------|--------|------|
| 01 | 类型定义 + Pi 写入适配器 | pending | `tasks/task-01.md` |
| 02 | OpenClaw 写入适配器 | pending | `tasks/task-02.md` |
| 03 | Hermes 写入适配器 | pending | `tasks/task-03.md` |
| 04 | AuthSyncService 核心 + Model API 重写 + 启动集成 | pending | `tasks/task-04.md` |
