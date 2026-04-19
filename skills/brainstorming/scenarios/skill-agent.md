# Scenario S2: Skill / Agent Development

> You have completed the common skeleton (Explore → Clarifying → Challenge Gate → Propose approaches). This file is the S2 SOP.

S2 covers the design of a new skill or agent (or a non-trivial redesign of one).

## When S2 applies

Explicit triggers:
- "设计 skill / skill 设计 / 新建 skill / skill brainstorm"
- "设计 agent / agent 设计 / 新建 agent / agent brainstorm"
- User describes wanting to build a reusable capability or specialized role

If ambiguous (e.g. "I want better memory handling"), ask the user which scenario before proceeding. Do not default to S2.

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

Save to `docs/brainstorming/specs/YYYY-MM-DD-<topic>-design.md` using the selected template (`skill-design-template.md` or `agent-design-template.md`).

### Step 5 — Spec review loop

Dispatch spec-document-reviewer subagent per `../references/spec-document-reviewer-prompt.md`. Max 3 iterations. Address blocking issues; advisory recommendations are discretionary.

### Step 6 — Produce skeleton

Create the empty skill/agent skeleton so the user can start implementing:

- **Skill:** `skills/<name>/{SKILL.md frontmatter-only stub, references/, assets/}`
- **Agent:** `agents/<name>.md` with frontmatter + identity section filled, body as TODO

### Step 7 — Recommend execution

Offer two paths for code implementation:
- **Inline** — if the skill/agent is simple, implement in the current session
- **Hand off to S3** — if implementation is substantial (multi-file, multi-phase), proceed as a feature story

## Gotchas

- Do not silently proceed with Path B when the identity audit fails — downgrade explicitly and tell the user why.
- The skeleton in Step 6 is **empty** by design; filling it is an execution concern, not a design concern.
- **Fast mode** applies here when the skill is trivial (single-purpose, < 50 lines SKILL.md, no references, no assets). In Fast mode, skip Steps 2-5 and go straight to inline implementation with a one-paragraph recommendation. Fast is a cost branch within S2, not a separate scenario.
