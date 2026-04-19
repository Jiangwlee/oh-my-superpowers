---
name: brainstorming
description: >-
  You MUST use this before any creative or implementation work — designing
  skills/agents, building features, fixing non-trivial bugs, refactoring.
  Triggers include: "设计 skill/agent"、"新建 skill/agent"、"skill/agent brainstorm"、
  "开发/实现/加功能/修复/重构 X". Turns ideas into a complete design through
  collaborative dialogue, then routes to the right scenario SOP (S1 open
  discussion / S2 skill-agent / S3 feature-refactoring). Do NOT use for pure
  factual lookups or questions with no creative or implementation intent.
---

# Brainstorming: Methodology + Scenario Router

<!--
  Scenario files (load the one that matches):
    - scenarios/open.md          S1 open discussion (fallback)
    - scenarios/skill-agent.md   S2 skill / agent development
    - scenarios/feature.md       S3 feature / refactoring

  Cross-cutting references (load on demand):
    - references/challenge-gate.md         Challenge Gate rules
    - references/risk-and-spike.md         Risk Register & Spike Loop
    - references/document-writing.md       Writing conventions + templates
    - references/principles-library.md     Action principles library
    - references/skill-fundamentals.md     Skill identity criteria (S2)
    - references/agent-fundamentals.md     Agent identity criteria (S2)
    - references/design-patterns.md        Skill pattern catalog (S2)
    - references/spec-document-reviewer-prompt.md   Spec review subagent prompt
-->

Turn ideas into complete designs through collaborative dialogue. This file is **methodology + router**. The detailed SOP lives in `scenarios/`.

<HARD-GATE>
Do NOT write code, scaffold a project, or take implementation action until the relevant scenario SOP has run and the user has approved the output. Fast mode (defined per scenario) exists for trivial tasks — it is not an excuse to skip brainstorming.
</HARD-GATE>

## Step 0 — Scenario routing

Before anything else, determine which scenario applies:

- **S2** (skill/agent): user says "设计 skill / agent"、"新建 skill / agent"、"skill/agent brainstorm" — or the topic is clearly about designing a reusable capability / specialized role.
- **S3** (feature/refactoring): user says "开发 / 实现 / 加功能 / 新增 / 修复 / 重构 / 改造 X" — or the topic is clearly an implementation job.
- **S1** (open discussion): fallback for everything else — the user wants to think, explore, or align understanding with no immediate implementation intent.

Matching order: **try S2 → try S3 → fall back to S1**. When the trigger is ambiguous (e.g. "I want X to be better"), **ask the user** which scenario applies; do not silently default.

Once matched, the rest of this file is the common skeleton; scenario-specific steps live in `scenarios/<matched>.md`.

## Common skeleton (all scenarios)

```
1. Explore project context — files, recent commits, ecosystem relevant to the scenario
2. Ask clarifying questions — purpose / scope baseline; further questions are heuristic
3. Challenge Gate — strongest objection + 3 checks (see references/challenge-gate.md)
4. Propose approaches — Normal: 2-3 options with trade-offs; inline-scope: direct recommendation
↓
Branch into scenarios/{open,skill-agent,feature}.md for the scenario-specific SOP
```

### Clarifying questions: principle

- **purpose** (what is this really trying to solve?) and **scope** (what is in / out?) are the **only preset baseline**.
- All other questions must be **heuristic** — based on specific ambiguities / conflicts / risks you actually observed during Explore. Ask 1-3 targeted questions, not a checklist.
- **Never ask preset scenario-specific questions.** Preset checklists kill brainstorming's core capability. Scenario files tell you what to **look at** during Explore, not what to **ask**.

### Ordering notes

- **Propose approaches before Risk & Spike.** Risk applies to specific proposals; risk without proposals is abstract anxiety. Risk & Spike lives inside each scenario's SOP (S2/S3), not in this common skeleton.

## Key principles

- **One question at a time** — avoid overwhelming the user.
- **Multiple choice preferred** — easier to decide than open-ended.
- **YAGNI ruthlessly** — remove unrequested features from all designs.
- **Incremental validation** — scenarios present design section-by-section, approval before moving on.
- **Action principles are the scenario's to pick** — default set: TDD · Break-Don't-Bend · Zero-Context Entry. See `references/principles-library.md` for the catalog.

## Producer contract (S3 only — full detail in scenarios/feature.md)

S3 hands off to coding-orchestrator via a four-artifact execution chain under `stories/<YYYY-MM-DD>-<slug>/`:
- `story.md` (narrative, **must** backlink the design doc)
- `tasks.yaml` (skeleton; wave≥2 has `spec: null`)
- `tasks/task-01.md` (wave-1 worker spec)
- `story-memory.md` (placeholder)

Design doc itself stays in `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`. brainstorming is the sole author; coding-orchestrator reads but does not write it. See `scenarios/feature.md` for the full contract.
