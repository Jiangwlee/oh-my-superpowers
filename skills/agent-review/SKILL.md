---
name: agent-review
description: >-
  Review and audit a Pi agent markdown file for spec compliance and design quality.
  Use when: reviewing an agent file, checking if an agent is ready to deploy,
  auditing agent description or system prompt quality.
  Do NOT use when: reviewing a skill directory (use skill-review), designing a new
  agent (use brainstorming), or testing agent runtime behavior.
---

# Agent Review

Purpose: Audit a Pi agent markdown file for spec compliance and design quality.
Input:   Agent file path from user.
Output:  Diagnostic report grouped by severity, with evidence and concrete fixes.

## Prerequisite Check

If the agent file path is not provided, ask before proceeding:

> Which agent file should I review? Please provide the path.
> Example: `agents/my-agent.md`

Verify the file exists and ends in `.md`. If not, stop and report.

## Workflow

### Phase 1: Load References

Read both reference files before starting the review:
- `references/agent-spec.md` — Pi frontmatter format rules and valid field values
- `references/rubric.md` — 8 review dimensions with criteria and severity guidance

### Phase 2: Frontmatter Review

Read the target agent file. Extract the YAML frontmatter block (between `---` delimiters).

Check against `agent-spec.md`:
- All four fields present: `name`, `description`, `tools`, `model`
- `name` matches the filename (without `.md` extension)
- `name` format: lowercase-hyphenated, 1–64 chars
- Each value in `tools` is from the valid list in `agent-spec.md`
- `model` is a recognized value

### Phase 3: System Prompt Review

Read the system prompt body (everything after the closing `---`).

Evaluate against all 8 dimensions in `rubric.md`:
1. Frontmatter 合规 (covered in Phase 2)
2. 身份清晰度
3. 输入规格
4. 工作流结构
5. 输出格式
6. 失败处理
7. Guardrails
8. 工具最小化

For each dimension: cite the exact line or section from the agent file as evidence. If a dimension passes cleanly, note it as passing — do not skip it silently.

### Phase 4: Write Report

Produce the diagnostic report using the Output Format below.

## Output Format

Start with this summary block:

```
## agent-review: <filename>
Found: X critical, Y warnings, Z suggestions.
Dimensions evaluated: 8 / 8
```

Use this format for each finding:

```
### [SEVERITY] Dimension N: <Dimension Name>

Labels: SPEC | BEST_PRACTICE | PROJECT_POLICY

**Issue:** One sentence describing the problem precisely.

**Evidence:**
<exact quote or concrete file state>

**Why it matters:**
<one sentence on impact>

**Suggested fix:**
<concrete replacement text or specific action>
```

Severity levels:
- `[CRITICAL]` — prevents correct loading or execution
- `[WARNING]` — degrades reliability or output quality
- `[SUGGESTION]` — improvement opportunity

Group findings: CRITICAL first, then WARNING, then SUGGESTION.

If a dimension has no issues, include a one-line pass note after the findings section.

## Done Criteria

- Both reference files were loaded before review started.
- All 8 dimensions were evaluated (none skipped).
- Every finding cites exact evidence from the agent file.
- Report starts with the summary block.
- Report language follows the user's language.

## Guardrails

**Every finding must cite an exact quote or concrete file state. No exceptions.**

- Do NOT invent issues. If you cannot point to a specific line, do not report it.
- Do NOT skip dimensions because the agent "looks fine". Evaluate all 8.
- Do NOT merge multiple distinct issues into one finding.
- Do NOT label a project preference as a spec violation.
