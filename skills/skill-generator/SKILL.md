---
name: skill-generator
description: >-
  Create a new Agent Skill from a requirement — grounding on what a skill is,
  clarifying what to build, picking a skill pattern, drafting SKILL.md plus
  references, and reviewing the result. Use when the user says "写个 skill",
  "创建 skill", "把这个能力做成 skill", "build a skill", "make a skill",
  or asks to author or scaffold a skill, even without naming the format.
  Do NOT use for restructuring an existing skill (skill-refine), auditing a
  finished skill (skill-review), or non-skill Markdown.
---
# Skill Generator

Purpose: Turn a requirement into a high-quality Agent Skill directory.
Input:   A capability the user wants to package, described in conversation.
Output:  A `skills/<name>/` directory (SKILL.md + references/, optional scripts/assets). Files only — no install, no publish.
Sections: Hard Gate | Core Principles | Workflow | References

**角色约定**：You are a **skill author**. 先打地基理解 skill，再与用户澄清需求，最后按规范起草并独立评审。只产出文件，不安装、不发布。

## Hard Gate

| 条件 | 动作 |
|---|---|
| 未读 `foundation.md` 就开始澄清需求 | 禁止；先走 Workflow 第 1 步（打地基） |
| 去掉 SKILL.md 及 references 后 LLM 仍能可靠完成该任务 | 告知用户「该能力无需封装为 skill」并停止；不要硬造（`foundation.md` §何时值得封装） |
| SKILL.md 塞入分支逻辑、长参考或详细规则 | 下沉到 `references/`，SKILL.md 只留骨架 + Hard Gate |
| 把 tests 放进 skill 目录 | 禁止；测试归 `tests/skills/<name>/` |
| 生成的 skill 依赖同项目其他 skill | 禁止；skill 必须自包含 |
| review 时把你的诊断/预期修法喂给 reviewer，或 subagent 可用却不独立评审 | 禁止；按第 5 步做独立评审 |
| 生成后执行 install 或 publish | 越界；交付边界是文件 |

## Core Principles

- **Predictability**：skill 的根德性 —— 让 agent 每次走**相同的过程**，不是产出相同的文本。
- **封装真实能力**：只封装真实工具/API/工作流/项目约定；不封装通用 LLM 知识。
- **渐进披露**：SKILL.md 是扉页 + 目录；能一句话讲清就内联，要展开才讲清就下沉 `references/`。
- **description 决定触发**：用祈使句写"何时用"，覆盖用户不点名领域的场景。
- **祈使句**：正文用命令式、强动词；硬约束用硬词（MUST / NEVER / 必须 / 不得）。

## Workflow

严格按序推进，每步达成 Done 判据才进入下一步。

1. **打地基** — 读 `references/foundation.md`。
   Done：能一句话说清「skill 是什么」和「这次要产出的目录长什么样」。
2. **澄清需求** — 每轮一个问题，问清：支持的任务、目标用户、1–2 个真实 prompt。答案空间已知时给选项。
   Done：三项已知，且通过「真实能力」判定（未通过 → 按 Hard Gate 第 2 条停止）。
3. **定模式** — 读 `references/patterns.md`，把需求归入 5 模式之一或其组合（Tool Wrapper / Generator / Reviewer / Inversion / Pipeline）。
   Done：模式已定，目录骨架已定。
4. **起草** — 读 `references/writing-conventions.md` 与 `references/wording.md`，写出 SKILL.md（骨架 + Hard Gate + Workflow）与 references。description 参照 Core Principles 第 4 条。
   Done：SKILL.md 与所有 references 成形，每个有序步骤都有可勾选的 Done 判据。
5. **自查 + 独立评审** — 先用 `references/self-check.md` 自查一遍。再 spawn 一个独立 reviewer subagent（若 `subagent`/`Task`/`Agent` 可用），**只给它**：草稿文件、`references/review-rubric.md`、用户的真实任务；**不给**你的推理或预期修法。修掉所有 blocking。subagent 不可用时，自己按 rubric 再审一遍并明确告知用户「本次评审非独立」。
   Done：无 blocking，或每条 blocking 已修。
6. **输出** — 交付 `skills/<name>/` 全部文件，列出文件清单与所属模式。不 install、不 publish。
   Done：文件写盘，清单已示。

## References

| 文件 | 层 | 何时读 |
|---|---|---|
| `references/foundation.md` | 概念/术语 + 地基 | 第 1 步，必读 |
| `references/philosophy.md` | 哲学（predictability 及其杠杆） | 起草前想不清"为什么这样切"时 |
| `references/patterns.md` | 5 种设计模式 | 第 3 步 |
| `references/writing-conventions.md` | 写法（结构 / 渐进披露 / 目录规范） | 第 4 步 |
| `references/wording.md` | 用词（祈使句 / 强动词 / 去解释） | 第 4 步 |
| `references/review-rubric.md` | 评审标准 | 第 5 步，喂给 reviewer |
| `references/self-check.md` | 生成后自查清单 | 第 5 步，起草者自查 |
