# Story: Backend Logger System

## Goal

为 mindora-ui 后端构建结构化日志系统（Pino），作为后端架构分层重构（0011）的 Phase 2。当前后端没有任何结构化日志，调试完全依赖 console.log。日志系统是后续所有 phase 的基础设施。

## Context

- Design: `docs/refactoring/0011-backend-architecture-layering-2026-04-11.md` §6.7
- Research: `docs/research/0003-backend-architecture-analysis-2026-04-11.md` §4 (pi-server 日志体系调研)
- Reference impl: `~/Github/pi-mono/packages/pi-server/` (Pino singleton + Proxy pattern)

## Scope

**In scope:**
- Pino singleton + Proxy 延迟初始化模块 (`src/lib/infra/logger.ts`)
- JSON(prod) / pino-pretty(dev) 双格式支持
- 环境变量配置: `LOG_LEVEL`, `LOG_FORMAT`
- 在现有关键路径插入日志点（registry.ts, bridge.ts, API routes）
- 单元测试: logger 初始化、级别过滤、子 logger 创建

**Out of scope:**
- 目录迁移（Phase 1，后续做）
- Event Bus 日志点（Phase 3 才有 Event Bus）
- 前端日志（前端不用 Pino）

## Tasks

| Task | Name | Status | Spec |
|------|------|--------|------|
| 01 | Pino logger 模块实现 | completed | `tasks/task-01.md` |
| 02 | 关键路径日志点注入 | completed | `tasks/task-02.md` |
