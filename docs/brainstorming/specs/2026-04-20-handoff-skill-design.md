# Skill Design: handoff

## 能力定义

- 封装的工具/规范/脚本：handover 文档生成模板（assets/）、PreCompact 阻断脚本、PostCompact pending 标记脚本、UserPromptSubmit 自动恢复脚本（均通过 CLI）
- 核心价值：「它让模型在 compaction 前生成结构化 handover 文档，并在 compaction 后自动恢复关键上下文，使后续 session 无缝衔接」
- 能力边界：
  - 能做：生成 handover 文档、PreCompact 时阻断并提醒、compaction 后自动注入 handover 内容
  - 不能做：自动执行 /compact（用户必须手动触发）、保证 compaction 后信息零丢失

## 设计模式

- 主模式：Generator（从模板生成结构化文档）
- 组合模式：Pipeline（4 步工作流）+ Hook 自动化（阻断 + 恢复）
- 选择理由：核心产物是填充模板生成的 .handover.md；三个 hooks 构成"阻断 → 标记 → 恢复"完整闭环

## 目录结构

```
skills/handoff/
├── SKILL.md
├── hooks.json
└── assets/
    └── handover-template.md

cli/handoff/
└── main.py                      ← omp handoff check / mark-pending / restore
```

> 主流程（SKILL.md Pipeline）LLM 直接用 Write tool 写文件，不需要 scripts/。
> CLI 仅服务三个 hook 命令。

## CLI 化方案

CLI 入口：`omp handoff`（模块路径：`cli/handoff/main.py`）

| 子命令 | 触发事件 | 行为 |
|--------|----------|------|
| `check --source <dir>` | `PreCompact` | `.handover.md` 不存在 → block；存在 → 静默放行 |
| `mark-pending --source <dir>` | `PostCompact` | 读 `.handover.md`，frontmatter 写入 `pending: true`，回写；输出 systemMessage |
| `restore --source <dir>` | `UserPromptSubmit` | 读 `.handover.md`，若 `pending: true` 则注入 additionalContext 并改为 `pending: false` 回写；否则静默 |

输出格式（JSON）：

```json
// check（.handover.md 不存在）
{
  "decision": "block",
  "reason": "⚠️ 未找到 .handover.md，建议先执行 /handoff 保存上下文，再运行 /compact"
}

// mark-pending
{
  "systemMessage": "📋 Handover 已标记，下一条消息将自动恢复上下文"
}

// restore（pending: true）
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "<.handover.md 全文>"
  }
}
```

## SKILL.md Frontmatter

```yaml
---
name: handoff
description: >-
  Use before running /compact to preserve session context. Generates a
  structured .handover.md and a ready-to-use /compact instruction so the
  next session resumes without information loss. Trigger when context
  reaches ~65-70%. Do NOT use for general summaries or task documentation.
---
```

## SKILL.md Body（Pipeline）

```
## Pipeline

Step 1 — 加载模板
  Read assets/handover-template.md

Step 2 — 填写 handover（启发式）
  逐 section 从当前对话上下文填写，遵循每个 section 的 guardrail。
  Key Decisions 包含所有本 session 的决策，含 Claude 自主做出的隐性选择。

Step 3 — 写入文件
  Write to .handover.md（项目根，覆盖已有内容）
  frontmatter 中 pending 初始为 false

Step 4 — 输出操作序列
  从 Key Decisions + Remaining Tasks 提炼关键词，生成 /compact 指令
  展示：
  ━━━ Handover saved → .handover.md ━━━
  ① /compact Focus on [task]. Preserve: [...]
  ② （PostCompact hook 将自动标记，下一条消息自动恢复）
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## assets/handover-template.md（6 sections）

YAML frontmatter 字段：`context_pct`、`timestamp`、`task_id`、`pending: false`

6 个 section + guardrail：

| # | Section | Guardrail |
|---|---------|-----------|
| 1 | Current Status | 描述"现在在哪里"：task 名 + 当前 phase + blocker；不列历史 |
| 2 | Completed Work | 文件名 + 一句描述；不写过程，不写已通过测试的细节 |
| 3 | Remaining Tasks | 按优先级，每条具体到可立即执行（含行号/函数名/端口等） |
| 4 | Key Decisions | 每条含 WHY；包含所有本 session 决策，含 Claude 隐性选择 |
| 5 | Active Files | 仅本 session 修改/创建的文件 + 当前状态（完成/中途/注意点） |
| 6 | Resume | 固定格式：`Read .handover.md and continue [exact next action]` |

## hooks.json

```json
{
  "hooks": {
    "PreCompact": [
      {"hooks": [{"type": "command", "command": "omp handoff check --source $PWD", "timeout": 3000}]}
    ],
    "PostCompact": [
      {"hooks": [{"type": "command", "command": "omp handoff mark-pending --source $PWD", "timeout": 3000}]}
    ],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "omp handoff restore --source $PWD", "timeout": 3000}]}
    ]
  }
}
```

## 渐进式披露规划

- SKILL.md body：Pipeline 4 步骤（精简）+ `Read assets/handover-template.md` 加载指令
- assets/handover-template.md：完整模板含 YAML frontmatter + 6 sections + guardrail 注释
- references/：无（设计足够简单）

## Trigger Eval

- 应触发：「帮我做 handoff」「context 快满了」「compact 前先保存上下文」「/handoff」
- 不应触发：「总结一下这次对话」「写个会议记录」「做个任务清单」

## T1 测试计划

- [ ] SKILL.md frontmatter 必填字段（name、description）存在且非空
- [ ] description 不含执行指令（只做语义触发）
- [ ] SKILL.md body 不含相对路径调用（无 `bash scripts/`、`python scripts/`）
- [ ] assets/handover-template.md 存在，包含全部 6 个 section header
- [ ] assets/handover-template.md frontmatter 含 `pending` 字段
- [ ] hooks.json 格式合法，包含 PreCompact、PostCompact、UserPromptSubmit 三个事件
- [ ] cli/handoff/main.py 存在，包含 check、mark-pending、restore 三个子命令
- [ ] `omp handoff check --source <dir>` 在无 .handover.md 时输出 `decision: block` JSON
- [ ] `omp handoff restore --source <dir>` 在 pending: false 时静默退出（exit 0，无 stdout）

## Risk Register

| 级别 | 假设 | 缓解措施 |
|------|------|----------|
| 🟡 | UserPromptSubmit 每条消息都跑 restore，uv 冷启动累积延迟 | pending: false 时静默退出，尽量快；可考虑 bash 做文件检查 |
| 🟡 | LLM 在 65%+ 压力下填写质量下降 | 固定 section 结构；鼓励在 65% 触发 |
| 🟢 | pending 字段存于 .handover.md，无第二个文件 | 单文件承载所有状态，stale 风险消除 |
| 🟢 | PreCompact block 机制 | 官方文档确认支持 |
| 🟢 | PostCompact → UserPromptSubmit 注入链 | UserPromptSubmit additionalContext 为官方文档确认能力 |
