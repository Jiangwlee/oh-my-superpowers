# Scenario S3: Feature / Refactoring

> You have completed the common skeleton (Explore → Clarifying → Challenge Gate → Propose approaches). This file is the S3 SOP.

S3 covers implementing a feature, fixing a non-trivial bug, or refactoring. It produces the handoff artifacts that coding-orchestrator consumes.

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

## SOP

### Step 1 — Risk & Spike

Read `references/risk-and-spike.md`. **Hard rule**: cannot finalize with unresolved 🔴 — run a spike first.

### Step 2 — Present design section-by-section

Use `assets/design-doc-template-normal.md` for standard scope, `assets/design-doc-template-fast.md` for single-file + unambiguous + zero 🔴 risk. Sections: 背景 → 设计方案 → 假设与风险登记 → Spike 计划/结果 → 行动原则 → 行动计划.

### Step 3 — Write design doc

Save to `docs/brainstorming/specs/YYYY-MM-DD-<slug>.md`. **brainstorming is the sole author**; coding-orchestrator reads but does not write this file.

### Step 4 — Spec review loop

Dispatch spec-document-reviewer subagent per `../references/spec-document-reviewer-prompt.md`. Max 3 iterations.

### Step 5 — Produce the four-artifact execution chain

Located at `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/`. The `YYYY-MM-DD` must match the design doc's date prefix.

#### 5.1 `story.md`

Complete narrative: goal, scope, constraints, high-level approach, acceptance criteria. **First line after the title must be the design doc backlink:**

```markdown
# Story: <slug>

> Design: /docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md
```

This backlink is **mandatory** — it's how orchestrator / worker / reviewer find the rationale.

#### 5.2 `tasks.yaml` (skeleton)

Follow `skills/coding-orchestrator/templates/tasks.yaml`. Skeleton contract:

```yaml
story: <slug>
created: <date>
updated: <date>

tasks:
  - id: "01"
    title: <action-oriented>
    status: pending
    wave: 1
    depends_on: []
    spec: tasks/task-01.md       # wave 1: non-null, must exist
    files_modified: [<estimate>]
    test_layer: integration
    # worker/reviewer/started/completed/commits/notes left for orchestrator

  - id: "02"
    title: <action-oriented>
    status: pending
    wave: 2
    depends_on: ["01"]
    spec: null                   # wave ≥ 2: null, orchestrator writes JIT
    files_modified: [<estimate>]
    test_layer: component
```

**brainstorming MUST write:**
- Complete dependency graph (`id / title / wave / depends_on`)
- `test_layer` per `skills/coding-orchestrator/references/task-decomposition-rules.md` Rule 1
- `files_modified` estimate per task
- **wave 1** tasks' `spec` pointing to real `tasks/task-NN.md` file

**brainstorming MUST NOT write:**
- wave ≥ 2 `tasks/task-NN.md` (orchestrator writes them JIT after prior wave's feedback)

**Self-check before saving**: run the Rule 1-5 checklist in `skills/coding-orchestrator/references/task-decomposition-rules.md`. If any rule fails, revise until it passes.

#### 5.3 `tasks/task-01.md` (and any other wave-1 task spec)

Use `skills/coding-orchestrator/templates/task.md`. Worker Refs section **must include** `../story-memory.md`.

#### 5.4 `story-memory.md` (placeholder)

Just the title line and the three section headers (Patterns / Gotchas / Known False Positives). Orchestrator fills it in as the story progresses. See `skills/coding-orchestrator/references/story-memory-guideline.md` for write rules.

### Step 6 — Hand off to coding-orchestrator

Notify the user: design is complete, skeleton is in place, coding-orchestrator should take over. Point at the story directory. The orchestrator's intake path for brainstorming handoffs is documented in `skills/coding-orchestrator/SKILL.md` under "Story Intake → Path A — handoff from brainstorming".

## Producer / consumer contract

- **brainstorming is the sole producer** of the design doc and the story skeleton.
- **coding-orchestrator is the consumer** — reads everything, writes wave≥2 task specs, updates tasks.yaml status, appends to story-memory.md. Does **not** modify the design doc or story.md.
- If design rationale needs revision mid-execution, coding-orchestrator halts and returns control to brainstorming (which runs spec review loop again if needed).

## Gotchas

- **Fast branch**: single-file + unambiguous + zero 🔴 risk → skip the entire execution chain; inline the recommendation. Fast is a cost branch within S3, not a separate scenario.
- **Cross-story scope**: if the Explore step shows the work spans multiple independent subsystems, recommend splitting into multiple stories (each with its own S3 pass), not one mega-story.
- **Break, Don't Bend**: default position is to remove the old implementation; do not add compat shims, legacy aliases, or v1/v2 coexistence unless the user explicitly justifies it.
