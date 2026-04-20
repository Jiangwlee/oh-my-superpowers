# Scenario S3: Feature / Refactoring

> You have completed the common skeleton (Explore → Clarifying → Challenge Gate → Propose approaches). This file is the S3 SOP.

S3 covers implementing a feature, fixing a non-trivial bug, or refactoring. Its sole deliverable is a design doc that coding-orchestrator consumes to generate the story skeleton.

## When S3 applies

Explicit triggers: "开发 / 实现 / 加功能 / 新增 / 修复 / 重构 / 改造 X"

If ambiguous (e.g. "I want X to be better"), ask the user which scenario before proceeding. Do not default to S3.

## Scenario exploration focus

During the common-skeleton Explore step, pay attention to:

- The code locations involved + recent commits touching them
- Whether the change crosses multiple independent subsystems (→ should split into multiple stories)
- Whether an old implementation exists (default is Break-Don't-Bend: remove, no compat shim)
- Related stories under `stories/` — similar slicing, gotchas already captured in their `story-memory.md`

Then in the common-skeleton Clarifying step, ask **heuristic** questions grounded in what you actually observed. Do not run through a preset checklist.

When discussing execution shape, brainstorming may suggest likely task merges / splits / wave boundaries, but it does **not** enforce the final task skeleton. That enforcement belongs to coding-orchestrator's Phase 1 skeleton review gate.

## SOP

### Step 1 — Risk & Spike

Read `references/risk-and-spike.md`. **Hard rule**: cannot finalize with unresolved 🔴 — run a spike first.

### Step 2 — Present design section-by-section

Use `assets/design-doc-template-normal.md` for standard scope, `assets/design-doc-template-fast.md` for single-file + unambiguous + zero 🔴 risk. Sections: 背景 → 设计方案 → 假设与风险登记 → Spike 计划/结果 → 行动原则 → 行动计划.

### Step 3 — Write design doc

Save to `docs/brainstorming/specs/YYYY-MM-DD-<slug>.md`.

### Step 4 — Spec review loop

Dispatch spec-document-reviewer subagent per `../assets/spec-document-reviewer-prompt.md`. Max 3 iterations.

### Step 5 — Hand off to coding-orchestrator

Notify the user that the design doc is complete and provide its path (`docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`). Recommend coding-orchestrator take over to generate the story skeleton.

Do **not** create `stories/<slug>/` or write any task artifacts — that is coding-orchestrator's job.

## Producer / consumer contract

- **brainstorming is the sole producer** of the design doc. brainstorming does not write anything under `stories/`.
- **coding-orchestrator is the consumer** — it reads the design doc and generates the story skeleton (`story.md`, `tasks.yaml`, `tasks/task-NN.md`, `story-memory.md`) on its own.
- If design rationale needs revision mid-execution, coding-orchestrator halts and returns control to brainstorming (which re-runs the spec review loop if needed).

## Gotchas

- **Fast branch**: skip Steps 1-5 entirely; inline the recommendation or implement directly in the current session. Fast is a cost branch within S3, not a separate scenario. Triggers when **any** of the following holds:
  - single-file + unambiguous + zero 🔴 risk
  - estimated scope ≤ 3 tasks AND < 5 files touched
- **Cross-story scope**: if the Explore step shows the work spans multiple independent subsystems, recommend splitting into multiple stories (each with its own S3 pass), not one mega-story.
- **Break, Don't Bend**: default position is to remove the old implementation; do not add compat shims, legacy aliases, or v1/v2 coexistence unless the user explicitly justifies it.
