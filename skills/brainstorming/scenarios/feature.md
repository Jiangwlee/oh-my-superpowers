# Scenario S3: Feature / Refactoring

> You have completed the common skeleton (Explore → Clarifying → Challenge Gate → Propose approaches). This file is the S3 SOP.

S3 covers implementing a feature, fixing a non-trivial bug, or refactoring. Its sole deliverable is a design doc at `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`.

## When S3 applies

Explicit triggers: "开发 / 实现 / 加功能 / 新增 / 修复 / 重构 / 改造 X"

If ambiguous (e.g. "I want X to be better"), ask the user which scenario before proceeding. Do not default to S3.

## Scenario exploration focus

During the common-skeleton Explore step, pay attention to:

- The code locations involved + recent commits touching them
- Whether the change crosses multiple independent subsystems (→ should split into multiple design docs, one brainstorming pass each)
- Whether an old implementation exists (default is Break-Don't-Bend: remove, no compat shim)
- Prior design docs under `docs/brainstorming/specs/` that touched similar code or captured related gotchas

Then in the common-skeleton Clarifying step, ask **heuristic** questions grounded in what you actually observed. Do not run through a preset checklist.

When discussing execution shape, brainstorming may sketch likely task decomposition as design-time hints, but it does **not** enforce the final breakdown — that decision sits outside brainstorming's scope.

## SOP

### Step 1 — Risk & Spike

Read `references/risk-and-spike.md`. **Hard rule**: cannot finalize with unresolved 🔴 — run a spike first.

### Step 2 — Present design section-by-section

Use `assets/design-doc-template-normal.md` for standard scope, `assets/design-doc-template-fast.md` for single-file + unambiguous + zero 🔴 risk. Sections: 背景 → 设计方案 → 假设与风险登记 → Spike 计划/结果 → 行动原则 → 行动计划.

### Step 3 — Write design doc

Save to `docs/brainstorming/specs/YYYY-MM-DD-<slug>.md`.

### Step 4 — Spec review loop

Dispatch spec-document-reviewer subagent per `../assets/spec-document-reviewer-prompt.md`. Max 3 iterations.

### Step 5 — Deliver design doc

Notify the user that the design doc is complete and provide its path (`docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`). brainstorming's deliverable ends here.

**Invariant**: brainstorming writes only the design doc under `docs/brainstorming/specs/`. Nothing else, no follow-up prescription — the caller decides what happens next.

## Gotchas

- **Fast branch**: skip Steps 1-5 entirely; inline the recommendation or implement directly in the current session. Fast is a cost branch within S3, not a separate scenario. Triggers when **any** of the following holds:
  - single-file + unambiguous + zero 🔴 risk
  - estimated scope ≤ 3 tasks AND < 5 files touched

  **Hard upgrade to Normal** (Fast disqualified regardless of the above) when the change touches either:
  - 持久化 shape — DB schema / 磁盘文件格式 / 外部序列化契约的迁移
  - auth / 权限路径 — credential lifecycle、token 传递、权限校验逻辑
- **Cross-story scope**: if the Explore step shows the work spans multiple independent subsystems, recommend splitting into multiple stories (each with its own S3 pass), not one mega-story.
- **Break, Don't Bend**: default position is to remove the old implementation; do not add compat shims, legacy aliases, or v1/v2 coexistence unless the user explicitly justifies it.
