# Skill Design: omp-agents

指导 claude/codex/pi 通过 `omp run` 委托任务给预定义 Pi Agent 的 Tool Wrapper skill。

## 目录

1. [能力定义](#能力定义)
2. [设计模式](#设计模式)
3. [目录结构](#目录结构)
4. [SKILL.md Frontmatter 草稿](#skillmd-frontmatter-草稿)
5. [SKILL.md 正文结构](#skillmd-正文结构)
6. [Trigger Eval](#trigger-eval)
7. [行动原则](#行动原则)
8. [行动计划](#行动计划)

---

## 能力定义

- **封装的工具/规范**：`omp run` CLI 调用规范 + agent 发现（`omp list -t agent`）+ 委托判断指南
- **核心价值**：「它让模型能够判断何时该委托任务给专业 agent，并正确调用 `omp run`」
- **能力边界**：
  - 能做：单 agent 委托（发现、选择、调用）
  - 不能做：多 agent 编排（那是 team skill 的职责）

## 设计模式

- **主模式**：Tool Wrapper
- **选择理由**：让模型成为 `omp run` 的专家，动态加载规范文档。纯知识型，无脚本。

## 目录结构

```
skills/omp-agents/
└── SKILL.md        # 唯一文件：frontmatter + 速查表 + 调用规范 + 委托指南
```

无 references/、assets/、scripts/ — 所有内容自包含在 SKILL.md 中。

## SKILL.md Frontmatter 草稿

```yaml
---
name: omp-agents
description: >-
  Use when a task matches a pre-defined Pi Agent's expertise.
  Delegate via omp run instead of doing it yourself.
  Do NOT use for multi-agent orchestration (use team skill).
---
```

## SKILL.md 正文结构

### 第 1 节：高频 Agent 速查表

| Agent | 擅长领域 | 典型任务 |
|-------|---------|---------|
| `researcher` | 深度研究、信息检索、网页调研 | "研究 X 技术的最新进展"、"对比 A 和 B 方案" |
| `reviewer` | Skill/Agent 质量审查 | "审查这个 skill 的 SKILL.md"、"检查 agent 定义是否合规" |
| `ux-engineer` | UI 审计、前端设计、风格优化 | "审计这个页面的 UI 问题"、"生成 Tailwind 组件" |

以上为高频子集。完整 agent 列表通过 `omp list -t agent` 动态获取。

### 第 2 节：调用规范

```bash
# 基本用法（推荐 stream 模式）
omp run <agent-name> --mode stream "任务描述"

# 指定模型
omp run <agent-name> --mode stream -m <model> "任务描述"

# 发现可用 agent
omp list -t agent
```

推荐模型：

| 模型 | 适用场景 |
|------|---------|
| `litellm-local/qwen3.5-27b` | 默认选择，本地推理，无成本 |
| `openai-codex/gpt-5.4` | 需要更高质量时使用 |

不推荐使用其他模型。

### 第 3 节：委托判断指南

**原则：能委托就委托，agent 有专业 skill 加持，比裸 LLM 效果更好。**

应该委托：
- 任务明确落在某个 agent 擅长领域
- 任务需要 agent 携带的专业 skill
- 当前 LLM 缺少相关工具或知识

不应该委托：
- 简单任务，直接做更快
- 需要多轮交互（omp run 是 one-shot）
- 需要当前对话上下文（agent 看不到对话历史）

Prompt 要求：
- 自包含 — agent 没有你的上下文，所有必要信息写进 prompt
- 明确输出格式 — 告诉 agent 要什么格式的结果
- 单一职责 — 一次只委托一件事

## Trigger Eval

- **应触发**：用户要求深度研究 / 审查 skill 或 agent / UI 审计或前端设计 / 其他匹配已注册 agent 的任务
- **不应触发**：简单问答 / 多 agent 编排（用 team）/ 当前对话能直接完成的任务

## 行动原则

1. **Break, Don't Bend** — 单文件 skill，不预留扩展点。
2. **Zero-Context Entry** — SKILL.md 前 20 行让读者立即理解用途和用法。
3. **Minimum Blast Radius** — 只创建一个文件，不改动现有代码。

## 行动计划

### 文件结构

```
skills/omp-agents/
└── SKILL.md
```

### 任务

#### Task 1: 创建 SKILL.md

创建 `skills/omp-agents/SKILL.md`，包含：
- frontmatter（name + description）
- 高频 Agent 速查表（researcher / reviewer / ux-engineer）
- 调用规范（omp run 参数 + 推荐模型 + stream 模式）
- 委托判断指南（何时委托 / 不委托 / prompt 要求）
- 发现命令（omp list -t agent）

#### Task 2: T1 验证

运行 `omp test omp-agents` 静态检查，确保 SKILL.md 格式合规。

---

**设计决策记录**：
- 不挂到任何 Pi agent 的 skills 列表 — 避免 agent 通过 omp run 调用 agent 的循环依赖
- 不设 references/ — 内容量少，全部自包含在 SKILL.md
- 与 team skill 独立 — team 管多 agent 编排，omp-agents 管单 agent 委托
- 推荐 stream 模式 — 实时看进度
- 只推荐两个模型 — litellm-local/qwen3.5-27b（默认）和 openai-codex/gpt-5.4（高质量）
