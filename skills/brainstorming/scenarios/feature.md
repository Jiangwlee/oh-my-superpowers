# Scenario S3: Feature / Refactoring

S3 覆盖实现一个 feature、修 non-trivial bug、或重构。唯一交付物：`docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`。进入本文件前必须已走完公共骨架（Phase 1-4）。

## When S3 applies

S3 适用于：用户要实现一个 feature、修 non-trivial bug 或重构。歧义时（如"I want X to be better"）必须明问，不得默认 S3。

> Note：触发短语清单在 `SKILL.md` description 中统一定义；本段只描述 routing 判据。

## Scenario exploration focus

During the common-skeleton Explore step, pay attention to:

- The code locations involved + recent commits touching them
- Whether the change crosses multiple independent subsystems (→ should split into multiple design docs, one brainstorming pass each)
- Whether an old implementation exists (default is Break-Don't-Bend: remove, no compat shim)
- Prior design docs under `docs/brainstorming/specs/` that touched similar code or captured related gotchas

Then in the common-skeleton Clarifying step, ask **heuristic** questions grounded in what you actually observed. Do not run through a preset checklist.

在 design doc 里可以 sketch 任务拆解作为设计提示，但不强制最终拆分——执行层自定。

## SOP

### Step 1 — Risk & Spike

Read `references/risk-and-spike.md`. **Hard rule**: cannot finalize with unresolved 🔴 — run a spike first.

### Step 2 — Present design section-by-section

Use `assets/design-doc-template-normal.md` for standard scope, `assets/design-doc-template-fast.md` for single-file + unambiguous + zero 🔴 risk. Sections: 背景 → 设计方案 → 假设与风险登记 → Spike 计划/结果 → 行动原则 → 行动计划.

### Step 3 — Write design doc

Save to `docs/brainstorming/specs/YYYY-MM-DD-<slug>.md`.

### Step 4 — Spec review loop

派遣 spec-document-reviewer 按 `../references/dispatch.md`（reviewer prompt 见 `../assets/spec-document-reviewer-prompt.md`）。最多 3 轮。处理 blocking issue；advisory 由主线判断是否采纳。

### Step 5 — Deliver design doc

通知用户 design doc 完成，附上路径（`docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`）。Brainstorming 的交付到此为止。

**Invariant**: brainstorming 只写 `docs/brainstorming/specs/` 下的 design doc，不做后续编排，由调用方决定下一步。

## Gotchas

- **Fast branch**: skip Steps 1-5 entirely; inline the recommendation or implement directly in the current session. Fast is a cost branch within S3, not a separate scenario. Triggers when **any** of the following holds:
  - single-file + unambiguous + zero 🔴 risk
  - estimated scope ≤ 3 tasks AND < 5 files touched

  **Hard upgrade to Normal**（Fast 直接失格）— 改动触碰任一条即必须 Normal：
  - 持久化 shape — DB schema / 磁盘文件格式 / 外部序列化契约的迁移
  - auth / 权限路径 — credential lifecycle、token 传递、权限校验逻辑
  - 跨独立子系统 — 同一改动横跨 ≥ 2 个独立模块/服务（拆 story 优先）
- **Cross-story scope**: if the Explore step shows the work spans multiple independent subsystems, recommend splitting into multiple stories (each with its own S3 pass), not one mega-story.
- **Break, Don't Bend**: default position is to remove the old implementation; do not add compat shims, legacy aliases, or v1/v2 coexistence unless the user explicitly justifies it.
