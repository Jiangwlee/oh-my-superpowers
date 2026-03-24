---
name: skill-brainstorming
description: >-
  Skill 设计工作流。在设计新 Skill 之前必须使用。通过真实能力检验、模式选择和逐步追问，
  将模糊的 Skill 想法转化为可执行的设计规格文档。
  Use when: user wants to design a new skill, says "设计一个 skill"、"我需要一个 skill"、
  "新建 skill"、"skill brainstorming"。
  Do NOT use for Agent 设计（使用 agent-brainstorming）、直接的代码实现任务、
  或没有明确 Skill 目标的通用功能头脑风暴（使用 brainstorming）。
---

# Skill Brainstorming

将模糊的 Skill 想法转化为完整的设计规格，通过真实能力检验和模式选择确保 Skill 有明确的设计意图。

<HARD-GATE>
不得跳过真实能力检验（Phase 0）和模式选择（Phase 2）直接进入设计。
不得在用户批准设计规格之前生成任何文件或调用 writing-plans。
</HARD-GATE>

## Checklist

按顺序创建 task 并逐一完成：

1. **Phase 0：真实能力检验** — 确认 Skill 封装的是真实工具/API/脚本/知识，而非可被模型直接完成的任务
2. **Phase 1：能力定义** — 精确描述封装的能力边界
3. **Phase 2：模式选择** — 从 5 种设计模式中选择，决定目录结构和 body 组织方式
4. **Phase 3：结构设计** — 根据模式确定文件组织（references/、assets/、scripts/）
5. **Phase 4：CLI 化设计** — 仅当模式涉及可执行脚本时进行
6. **Phase 5：触发边界设计** — 设计 description、Use when、Do NOT use when
7. **Phase 6：渐进式披露规划** — 划分 SKILL.md body 与 references/ 的内容边界
8. **Phase 7：规格生成** — 生成设计规格文档，提交，调用 writing-plans

## Phase 0：真实能力检验（Hard Gate）

逐一提问，每次只问一道：

> Q1：这个 Skill 要封装的是什么？它依赖哪些具体的工具、API、脚本、库规范或专业知识体系？

> Q2：如果没有这个 Skill，模型能用通用知识直接完成同样的任务吗？

**判定规则：**

- 没有具体工具/API/规范/脚本依赖，只是"让模型做 X" → **失败**
- Q2 回答"能" → **失败**，不需要 Skill，直接用模型即可

失败时终止并告知：

> 这个需求不需要 Skill。Skill 的价值在于封装模型自身无法直接完成的能力——
> 特定工具的操作、内部编码规范、可执行脚本、专有知识体系等。
> 建议直接使用模型，或重新思考需要封装的具体能力是什么。

通过后继续 Phase 1。

## Phase 1：能力定义

基于 Phase 0 的答案，逐步确认：

> 这个 Skill 封装的核心能力是什么？用一句话描述：「它让模型能够 ___」

> 这个能力的边界在哪里？哪些事情它能做，哪些不能做？

每次只问一个确认问题。

## Phase 2：模式选择（Hard Gate）

从 5 种设计模式中选择，这决定了后续所有设计决策。

展示决策表，请用户选择：

```
┌─────────────────┬──────────────────────────────────┬──────────────────────┐
│ 模式             │ 适用场景                           │ 核心机制              │
├─────────────────┼──────────────────────────────────┼──────────────────────┤
│ Tool Wrapper    │ 让模型成为特定技术/库的专家          │ 动态加载规范，按需注入  │
│ Generator       │ 从模板生成结构化文档/代码            │ 模板驱动，强制输出结构  │
│ Reviewer        │ 按标准检查内容，按严重程度分类        │ 模块化评分标准         │
│ Inversion       │ 先收集需求再行动                    │ 多轮追问，门控机制      │
│ Pipeline        │ 严格的多步骤工作流，需要检查点        │ 顺序步骤，用户确认      │
└─────────────────┴──────────────────────────────────┴──────────────────────┘
```

> 根据你描述的能力，这个 Skill 最接近哪种模式？可以是组合（如 Pipeline + Reviewer）。

确认模式后，告知其对应的目录结构和文件组织方式（见 Phase 3）。

## Phase 3：结构设计

加载 `references/design-patterns.md`，找到选定模式的目录结构，逐步确认每个目录的具体文件。若模式组合，合并对应结构。

## Phase 4：CLI 化设计

**仅适用于**：Pipeline 中涉及可执行脚本的步骤，或 Tool Wrapper 封装的是 CLI 工具。

> 脚本的命令接口是什么？入参和输出格式是什么？
> （示例：`mytool fetch --date 2026-03-24` → JSON 数组）

确认 CLI 化方案：脚本放 `scripts/`，通过 `omp` 或独立命令暴露，SKILL.md 中只写命令名，不写路径。

若模式不涉及脚本（Generator / Reviewer / Inversion / 纯文档型 Tool Wrapper），**跳过此阶段**。

## Phase 5：触发边界设计

逐步确认 description 的三个要素：

> 在哪些场景下应该触发这个 Skill？（Use when）

> 有哪些相似场景容易误触发，需要明确排除？（Do NOT use when）

> 用一句话概括这个 Skill 的核心价值，用于 description 的第一句。

检查触发边界是否清晰，是否与现有 Skill 存在重叠。

## Phase 6：渐进式披露规划

> SKILL.md 的 body 里应该放什么？（触发后模型立即需要的：工作流步骤、核心指令）

> 哪些内容可以放到 `references/` 或 `assets/` 按需加载？（详细规范、模板、检查清单）

原则：body 只放"做什么/怎么做"的主线逻辑，细节内容全部外部化到文件中，在需要时显式加载。

## Phase 7：规格生成

加载 `assets/skill-design-template.md`，按模板填写各节内容后写入：

```
docs/design/YYYY-MM-DD-<skill-name>-design.md
```

提交设计文档，然后：

> 设计规格已写入 `<path>`，请确认无误后我们继续制定实现计划。

等待用户确认，然后调用 **writing-plans** skill。

## 关键原则

- **一次一个问题** — 不堆叠多个问题
- **真实能力检验不可跳过** — 再简单的 Skill 需求也要过 Phase 0
- **模式选择不可跳过** — 模式决定目录结构和 body 写法
- **CLI 化按需** — 只有涉及可执行脚本的模式才需要 CLI 化设计
- **渐进式披露** — body 只放主线逻辑，细节全部外部化
- **规格优先于实现** — 设计文档批准前不生成任何代码文件
