---
name: deep-research
description: >-
  Use when a task requires systematic multi-round research across multiple
  angles, sources, and validation steps before producing a conclusion or
  report. Do NOT use when a quick ad-hoc search, a single-page summary, or a
  one-off fact lookup is enough.
---

# deep-research Skill

把"搜一搜"升级为"有节奏的多轮研究"：拆目标 → broad 探索 → 定向深挖 → 补反方 → 输出可审计的 `brief` + `full report`。

**适用**：需要跨多角度、多来源、多轮验证才能下结论。
**不适用**：一次性临时搜索、单页总结、单一事实查询。

## 工作流骨架

| Phase | 产出 | 详见 |
|---|---|---|
| 0. Clarify Goal | `plan.md`（3-6 条子问题，带 checkbox） | `references/methodology.md` |
| 1. Broad Exploration | 维度地图、关键词、关键实体 | 同上 |
| 2. Deep Dive | 关键全文 + Pre-search Reasoning 块 | 同上 |
| 3. Diversity & Validation | 反方、限制、替代、风险 | 同上 |
| 4. Synthesis Check | `[Round N Synthesis]` 状态块，更新 plan | `references/stop-criteria.md` |
| Report | `brief.md` + `full-report.md` | `references/reporting.md` |

未覆盖多角度、缺关键全文来源、缺反方 / 限制信息 → 不得提前停止。

## CLI 入口

```bash
omp deep-research <subcommand> [args]
```

| 命令 | 作用 |
|---|---|
| `init` | 创建 workspace（`--topic` / `--slug` / `--mode`） |
| `build-report` | 写入 brief + full report，并把 sources 持久化到 `state.json` |

不确定参数先跑 `omp deep-research <subcommand> --help`，或查 `references/cli.md`。

## 搜索工具

**优先** `omp web-operator`：`search-multi` 一次覆盖多个互补平台，`read-url` 读全文（已适配 reddit / x / xueqiu / taoguba 等动态站点）。失败再降级到 WebSearch / WebFetch。不要手搓 CDP 或用 curl 抓页面。

来源优先级、中英文覆盖、平台矩阵 → `references/source-strategy.md`。

## 数据目录

默认：`~/.local/share/oh-my-superpowers/deep-research/`，可用 `DEEP_RESEARCH_DATA_DIR` 覆盖。workspace 结构 → `references/workspace.md`；`state.json` schema → `references/state-schema.md`。

## 按需加载

| 何时读 | 文档 |
|---|---|
| 理解完整流程和每个 Phase 的产物 | `references/methodology.md` |
| 决定搜什么、信什么来源 | `references/source-strategy.md` |
| 判断是否停止本轮研究 | `references/stop-criteria.md` |
| 写 brief / full report | `references/reporting.md` |
| CLI 子命令与参数 | `references/cli.md` |
| `state.json` 结构 | `references/state-schema.md` |
| workspace 目录结构 | `references/workspace.md` |
