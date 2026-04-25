# Scenario S2: Skill / Agent Development

S2 covers the design of a new skill or agent, or a non-trivial redesign of one. 进入本文件前必须已走完公共骨架（Phase 1-4）。

## When S2 applies

S2 适用于：用户要设计一个可复用能力（skill）或专职角色（agent）。歧义时（如"I want better memory handling"）必须明问，不得默认 S2。

> Note：触发短语清单在 `SKILL.md` description 中统一定义；本段只描述 routing 判据。

## Scenario exploration focus

During the common-skeleton Explore step, pay attention to:

- Current `skills/` and `agents/` inventory — is there an existing one to extend/replace?
- The identity criteria in `references/skill-fundamentals.md` (Skill) and `references/agent-fundamentals.md` (Agent)
- Signals in the user's phrasing: trigger language, intended caller, scope (is this a skill the LLM invokes, or a tool a human invokes?)

Then in the common-skeleton Clarifying step, ask **heuristic** questions grounded in what you actually observed. Do not run through a preset checklist.

## SOP

### Step 1 — Identity audit

Run the identity check appropriate to the user's stated kind:

**Path A (Skill):** Read `references/skill-fundamentals.md` + `references/design-patterns.md`. Run capability check and pattern selection. Pass → go to Step 2 with `assets/skill-design-template.md`. Fail → scenario degrades to S1 (the request isn't a skill; help the user think it through instead).

**Path B (Agent):** Read `references/agent-fundamentals.md`. Run the Role / Agency / Ownership audit. Pass → go to Step 2 with `assets/agent-design-template.md`. Fail → auto-downgrade to Path A (agent judgment not warranted; reconsider as a skill).

### Step 2 — Risk & Spike

Read `references/risk-and-spike.md`. List assumptions this design bets on, classify 🟢 / 🟡 / 🔴. **Hard rule**: cannot finalize with unresolved 🔴 — run a spike first.

### Step 3 — Present design section-by-section

Present each section to the user, get approval before moving to the next: identity → SOP → guardrails → assets / references → success criteria. Use the template selected in Step 1.

### Step 4 — Write design doc

Save to `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md` using the selected template (`skill-design-template.md` or `agent-design-template.md`).

### Step 5 — Spec review loop

派遣 spec-document-reviewer 按 `../references/dispatch.md`（reviewer prompt 见 `../assets/spec-document-reviewer-prompt.md`）。最多 3 轮。处理 blocking issue；advisory 由主线判断是否采纳。

### Step 6 — Produce skeleton

Create the empty skill/agent skeleton so the user can start implementing:

- **Skill:** `skills/<name>/{SKILL.md frontmatter-only stub, references/, assets/}`
- **Agent:** `agents/<name>.md` with frontmatter + identity section filled, body as TODO

### Step 7 — Recommend execution

Offer two paths for code implementation:
- **Inline** — if the skill/agent is simple, implement in the current session
- **Hand off to S3** — if implementation is substantial (multi-file, multi-phase), proceed as a feature story

## Gotchas

- Path B identity audit 失败时，显式降级到 Path A 并告知用户原因，禁止静默继续。
- Step 6 skeleton 是**空骨架**——填充是执行任务，不是设计任务。
- **Fast mode** 触发：skill 单一职责、SKILL.md < 50 行、无 references、无 assets。Fast 跳过 Steps 2-5，直接 inline 实现 + 一段话推荐。
