# Agent Review Rubric

Purpose: Define evaluation criteria for the 8 review dimensions.
Input:   Loaded by agent-review during semantic review.
Output:  Reference only. Defines dimensions, criteria, labels, and severity guidance.

---

## Dimension 1: Frontmatter 合规

**What to check:**
- All four fields present: `name`, `description`, `tools`, `model`
- `name` matches the filename (without `.md`)
- `name` is lowercase-hyphenated, 1–64 chars, no leading/trailing/consecutive hyphens
- `description` is non-empty and under 1024 characters
- All values in `tools` are from the valid list in `agent-spec.md`
- `model` value is a recognized model ID

**Severity:**
- `[CRITICAL]` — missing required field; `name` does not match filename; invalid `tools` value
- `[WARNING]` — `description` over 1024 chars; non-standard `model` value without justification

---

## Dimension 2: 身份清晰度

**What to check:**
- The system prompt opens with a clear role statement (e.g., "You are a X specialist")
- The role maps to a specific professional function, not a generic description
- The agent has at least one explicit constraint or iron law (something it must or must never do)

**Severity:**
- `[WARNING]` — role is generic ("You are a helpful assistant") or absent
- `[SUGGESTION]` — role exists but lacks specificity or constraints

---

## Dimension 3: 输入规格

**What to check:**
- The system prompt specifies what input the user must provide
- There is explicit handling for missing input (ask the user, not assume or fail silently)

**Severity:**
- `[WARNING]` — agent proceeds without verifying required input is present
- `[SUGGESTION]` — input is handled but the prompt to the user is vague

---

## Dimension 4: 工作流结构

**What to check:**
- The system prompt defines a clear sequence of steps or phases
- Steps are numbered, labeled, or otherwise ordered — not a flat paragraph
- Each step has a clear action (not vague instructions like "handle the task")

**Severity:**
- `[WARNING]` — workflow is a flat block of prose with no discernible structure
- `[SUGGESTION]` — steps exist but are inconsistently named or ordered

---

## Dimension 5: 输出格式

**What to check:**
- The system prompt defines what the output should look like
- If output is structured (report, list, table), a template or example is provided
- Done criteria are explicit: the agent knows when it has finished

**Severity:**
- `[WARNING]` — output format is unspecified for a task with non-obvious output shape
- `[SUGGESTION]` — output guidance exists but no concrete template or done criteria

---

## Dimension 6: 失败处理

**What to check:**
- The system prompt addresses what to do when expected input is missing or malformed
- Edge cases (file not found, empty input, ambiguous request) have explicit branches
- Failure paths guide the user toward a valid state rather than silently stopping

**Severity:**
- `[WARNING]` — no failure handling; agent will stall or produce nonsense on bad input
- `[SUGGESTION]` — some failure handling present but incomplete for likely edge cases

---

## Dimension 7: Guardrails

**What to check:**
- There is an explicit list of things the agent must NOT do
- Guardrails use strong language ("must not", "never", "do not") — not soft suggestions
- Constraints are specific, not generic ("do not make mistakes")

**Severity:**
- `[WARNING]` — no guardrails section for an agent that could cause irreversible actions
- `[SUGGESTION]` — guardrails exist but use weak or vague language

---

## Dimension 8: 工具最小化

**What to check:**
- Every tool listed in the `tools` field is actually used in the workflow
- No tools are listed "just in case"
- If `bash` is listed, there is a concrete reason (e.g., running a script, not just reading files)

**Severity:**
- `[WARNING]` — tools listed that are clearly not needed by the described workflow
- `[SUGGESTION]` — tool list is plausible but could be trimmed

---

## Label Rules

- `SPEC` — grounded in the Pi agent format spec (`agent-spec.md`)
- `BEST_PRACTICE` — broadly useful design guidance
- `PROJECT_POLICY` — oh-my-superpowers specific conventions

A finding may carry more than one label. Do not label a project preference as `SPEC`.

---

## Severity Guide

| Level | Definition |
|-------|------------|
| `[CRITICAL]` | The agent will fail to load, fail to execute correctly, or is likely to produce broken output. |
| `[WARNING]` | The agent will probably work, but reliability or output quality is meaningfully degraded. |
| `[SUGGESTION]` | The agent works; there is a defensible improvement in clarity or design. |
