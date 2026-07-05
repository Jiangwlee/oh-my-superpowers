# Patterns — 5 种设计模式

Purpose: 把需求归入一种（或组合）经典 skill 模式。模式决定目录结构和 SKILL.md body 的写法。第 3 步用本文件定型。
Sections: 选型 | Tool Wrapper | Generator | Reviewer | Inversion | Pipeline | 组合

## 选型

每个 skill 必须属于或组合下列模式之一。按需求的**核心动作**选：

| 需求的核心动作 | 模式 |
|---|---|
| 让 agent 成为某工具/库/API 的专家 | **Tool Wrapper** |
| 从模板生成结构化文档/代码 | **Generator** |
| 按标准检查内容，按严重度分类 | **Reviewer** |
| 先多轮收集需求，再行动 | **Inversion** |
| 严格的多步骤工作流，带检查点 | **Pipeline** |

一个 skill 可组合多种（如 Pipeline + Reviewer）。`skill-generator` 自身就是 Inversion + Pipeline + Reviewer。

## Tool Wrapper

让模型成为特定技术/库/API 的专家。

- 核心文件：`references/conventions.md`（或 `cli.md`）—— 工具的用法、参数、输出 schema、边界。
- SKILL.md body：一段最短工作流 + 指向 reference 的 pointer。把"完整参数表"下沉。
- 判定：agent 不看 skill 就会用错这个工具吗？会 → 值得。

```
<name>/
├── SKILL.md
└── references/conventions.md
```

## Generator

从模板生成结构化文档或代码。

- 核心文件：`assets/<template>.md`（输出骨架）+ `references/style-guide.md`（填写规范）。
- SKILL.md body：加载 template → 按 style-guide 填 → 输出。把"每字段怎么填"下沉 style-guide。
- 关键：**先让 agent 看到期望输出的样子**（template），再开始填。

```
<name>/
├── SKILL.md
├── assets/<template>.md
└── references/style-guide.md
```

## Reviewer

按标准检查内容，按严重度分类输出。

- 核心文件：`references/review-checklist.md` —— 检查项 + 每项的 reject 条件 + 严重度。
- SKILL.md body：加载 checklist → 逐项扫 → 按 `blocking` / `polish` 分类报告。
- 输出契约：每个发现给 `file / quote / problem / severity / rewrite`。
- 独立性：可用 subagent 时独立评审，只喂产物与 checklist，不喂诊断。

```
<name>/
├── SKILL.md
└── references/review-checklist.md
```

## Inversion

先多轮收集需求，再行动（"反转"：不是拿到任务就做，而是先问）。

- 核心文件：`assets/<output-template>.md` —— 收集完成后要填的结构。
- SKILL.md body：每轮一个问题 → 答案空间已知时给选项 → 收满才行动。
- 关键 Done 判据：需要的字段**全部**已知，才允许进入行动步。

```
<name>/
├── SKILL.md
└── assets/<output-template>.md
```

## Pipeline

严格的多步骤工作流，带检查点。

- 核心：各步骤按需加载 `references/` 和 `assets/`。
- SKILL.md body：有序 Step 列表，每步一句 brief + 一个可检验 Done 判据 + 按需 load pointer。
- 关键：把后续步骤的细节下沉，避免 agent 看到后续就赶（premature completion）。

```
<name>/
├── SKILL.md
├── references/<step-detail>.md
└── assets/<step-artifact>.md
```

## 组合

模式组合时，目录合并、SKILL.md 以主干模式的骨架为准，其余模式作为其中某步的形态。例：一个 Pipeline，其"起草"步是 Generator、"评审"步是 Reviewer —— 目录含 `assets/`（Generator）+ `references/review-checklist.md`（Reviewer），SKILL.md 是 Pipeline 的有序步骤。

组合时只保留主干模式必需的目录；被组合模式若其核心文件在本 skill 无实际内容，可省略（如 `skill-generator` 是 Inversion + Pipeline + Reviewer，但澄清用对话完成、无固定输出模板，故不含 `assets/`）。
