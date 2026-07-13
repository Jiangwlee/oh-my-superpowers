---
name: cli-review
description: >-
  Review an agent-facing CLI's source code against the 10 AXI (Agent
  eXperience Interface) design principles, and produce a Markdown report of
  violations with fixes. Use when the user asks to review, audit, or check
  whether a CLI is agent-ergonomic / agent-friendly, whether its output is
  token-efficient, or whether a coding agent will misread its output — even
  without naming AXI. Do NOT use for CLIs meant for human interactive use
  (colored TUIs, prompts-by-design), for non-CLI code review, or for runtime
  behavior testing.
---
# CLI Review (AXI)

Purpose: Statically review one agent-facing CLI's source against the 10 AXI principles; report violations with fixes.
Input:   A path to CLI source (repo, package, or entrypoint) from the user.
Output:  A Markdown report — per-principle findings (severity, `file:line`, problem, fix) + a compliance summary.
Sections: Hard Gate | Workflow | References

**角色约定**：You are a **static CLI reviewer**. Read source only — never run the CLI, never edit it. Every finding must cite `file:line` from source you actually read.

## Hard Gate

| 条件 | 动作 |
|---|---|
| 目标 CLI 是给人交互用的（TUI/彩色表格/prompt-by-design） | 停止评审。告知用户 AXI 只适用于 agent 通过 shell 消费的 CLI，请确认对象后再来 |
| 未加载 `references/axi-principles.md` 就开始判定 | 禁止；先走 Workflow 第 2 步 |
| 未读到源码就报某条违规 | 禁止；每个 finding 必须引 `file:line`，未读到证据的原则标 `unverified` 不标违规 |
| 运行该 CLI、改其源码、跑测试 | 越界；本 skill 纯静态只读 |
| 混淆严重度 | 严重度判据以 `references/axi-principles.md`「严重度定义」为唯一准绳，不得自拟 |
| 报告未按 `assets/report-template.md` 结构输出 | 禁止；按模板输出 |

## Workflow

1. **定位入口** — 找到 CLI 的命令分发层（arg parser / 子命令 handler / stdout 写点 / exit code 设置点）。列出要读的文件。
   Done：命令分发入口、输出边界、错误处理三处的文件路径已定位。
2. **加载清单** — 读 `references/axi-principles.md`。对每条原则，掌握它的违规信号、源码定位线索、严重度。
   Done：10 条原则的检查要点在手。
3. **逐条扫描** — 按清单逐条比对源码。每条得出：`compliant` / `violation` / `unverified`（源码未覆盖到，无法判定）。违规必须引 `file:line` + 引用相关源码片段。
   Done：10 条原则各有裁定，违规项均有 `file:line` 证据。
4. **定严重度与修复** — 每个 violation 按 `references/axi-principles.md` 的「严重度定义」标 `blocking` 或 `advisory`，给出具体修复方向（改哪里、改成什么）。
   Done：每个 finding 有严重度 + 可执行修复建议。
5. **出报告** — 读 `assets/report-template.md`，按其结构输出 Markdown 报告。
   Done：报告含逐条 findings + 合规汇总表，写给用户。

## References

| 文件 | 作用 | 何时读 |
|---|---|---|
| `references/axi-principles.md` | 10 原则检查清单：违规信号 + 源码定位线索 + 严重度 | 第 2 步，必读 |
| `assets/report-template.md` | Markdown 报告输出骨架 | 第 5 步 |
