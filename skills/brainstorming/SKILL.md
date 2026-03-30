---
name: brainstorming
description: >-
  You MUST use this before any creative work - creating features, building
  components, adding functionality, or modifying behavior. Also covers Skill
  and Agent design: "设计一个 skill"、"设计一个 agent"、"新建 skill/agent"、
  "skill brainstorm"、"agent brainstorm". Turns ideas into a complete design +
  action plan through collaborative dialogue, then hands off to execution.
  Do NOT use for pure research or questions with no implementation intent.
---

# Brainstorming: Ideas → Design + Action Plan

<!--
  关键引用（按需加载，不要一次全读）：
    - references/challenge-gate.md         Challenge Gate 详细规则
    - references/document-writing.md       文档撰写规范和模板索引
    - references/principles-library.md     固定原则库（7 条）
    - references/skill-fundamentals.md     Skill 自治原则和判断标准
    - references/design-patterns.md        5 种 Skill 模式定义
    - references/agent-fundamentals.md     Agent 身份标准和判断规则
    - spec-document-reviewer-prompt.md     Spec 审查 subagent 提示词
    - visual-companion.md                  可视化伴侣使用指南
-->

Turn ideas into complete designs and action plans through collaborative dialogue.

<HARD-GATE>
Do NOT write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY request regardless of perceived simplicity — Fast mode exists for simple tasks.
</HARD-GATE>

## Checklist

Create a task for each item and complete them in order:

1. **Explore project context** — check files, docs, recent commits
2. **Topic-specific Gate** — if user explicitly mentions "skill" or "agent", run pre-check (see below); otherwise skip
3. **Offer visual companion** — if topic involves visual questions, offer once in its own message; read `visual-companion.md` if accepted
4. **Ask clarifying questions** — one at a time; purpose, constraints, success criteria
5. **Challenge Gate** — surface the strongest objection before proposing solutions; read `references/challenge-gate.md` for the 3 checks and rules
6. **Judge mode** — default Normal; switch to Fast when single-file, unambiguous, obvious solution
7. **Propose approaches** — Normal: 2-3 options with trade-offs; Fast: recommendation directly
8. **Present design** — section by section, get user approval after each (设计方案 + 行动原则)
9. **Write implementation plan** — read `references/document-writing.md` 行动计划撰写约束; scope check → file structure → task 分解; present to user for approval
10. **Write unified doc** — merge design + plan into single doc; read `references/document-writing.md` for templates; save to `docs/brainstorming/specs/YYYY-MM-DD-<topic>-design.md`
11. **Spec review loop** — (Normal only) dispatch spec-document-reviewer subagent (covers both design and plan); max 3 iterations
12. **User reviews doc** — ask user to confirm before proceeding
13. **Recommend execution** — "多模块/5+ tasks 建议 subagent 逐 task 执行；简单任务建议 inline 执行"

## Topic-specific Gate (Step 2)

Only activate when the user **explicitly mentions** "skill" or "agent", or when context is unambiguous. Otherwise skip to Step 3.

**Path A — Skill Gate:** Read `references/skill-fundamentals.md` and `references/design-patterns.md`. Run capability check and pattern selection per those docs. Pass → proceed with `assets/skill-design-template.md`. Fail → terminate or adjust.

**Path B — Agent Gate:** Read `references/agent-fundamentals.md`. Run identity audit per that doc. Pass → proceed with `assets/agent-design-template.md`. Fail → auto-downgrade to Path A.

## Key Principles

- **One question at a time** — don't overwhelm
- **Multiple choice preferred** — easier than open-ended
- **YAGNI ruthlessly** — remove unrequested features from all designs
- **Incremental validation** — present section by section, get approval before moving on
- **Principles from library** — read `references/principles-library.md`; default: TDD · Break Don't Bend · Zero-Context Entry
