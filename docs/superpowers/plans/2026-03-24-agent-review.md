# agent-review Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `agent-review` skill — a Reviewer-pattern skill that audits Pi agent markdown files against a spec and quality rubric, outputting a structured diagnostic report.

**Architecture:** Pure Reviewer pattern with no scripts. All evaluation knowledge lives in `references/agent-spec.md` (Pi frontmatter format rules) and `references/rubric.md` (8 quality dimensions). The SKILL.md body contains only the workflow and output template. T1 static tests validate file existence and content completeness.

**Tech Stack:** Markdown files only. T1 tests in Python (pytest + `py_compile`).

---

## File Structure

```
skills/agent-review/
├── SKILL.md                    # Frontmatter + workflow + output format + guardrails
├── references/
│   ├── README.md               # Index: scenario → file mapping
│   ├── agent-spec.md           # Pi agent frontmatter spec + valid tools/models
│   └── rubric.md               # 8 review dimensions with criteria and severity
└── tests/
    └── test_static.py          # T1: file existence + content completeness checks
```

---

## Task 1: Bootstrap directory and T1 test scaffold

**Files:**
- Create: `skills/agent-review/tests/test_static.py`

- [ ] **Step 1: Create the skill directory structure**

```bash
mkdir -p skills/agent-review/references skills/agent-review/tests
```

- [ ] **Step 2: Write the T1 test file**

```python
# skills/agent-review/tests/test_static.py
"""T1 static checks for agent-review skill."""
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent


def test_skill_md_exists():
    assert (SKILL_ROOT / "SKILL.md").exists()


def test_skill_name_matches_directory():
    content = (SKILL_ROOT / "SKILL.md").read_text()
    assert re.search(r"^name:\s*agent-review\s*$", content, re.MULTILINE), (
        "SKILL.md frontmatter name must be 'agent-review'"
    )


def test_references_readme_exists():
    assert (SKILL_ROOT / "references" / "README.md").exists()


def test_agent_spec_exists():
    assert (SKILL_ROOT / "references" / "agent-spec.md").exists()


def test_agent_spec_has_tools_list():
    content = (SKILL_ROOT / "references" / "agent-spec.md").read_text()
    for tool in ["read", "bash", "edit", "write", "grep", "find", "ls"]:
        assert tool in content, f"agent-spec.md must list valid tool: {tool}"


def test_rubric_exists():
    assert (SKILL_ROOT / "references" / "rubric.md").exists()


def test_rubric_covers_all_dimensions():
    content = (SKILL_ROOT / "references" / "rubric.md").read_text()
    dimensions = [
        "Frontmatter",
        "身份",
        "输入",
        "工作流",
        "输出",
        "失败",
        "Guardrail",
        "工具",
    ]
    for dim in dimensions:
        assert dim in content, f"rubric.md must cover dimension: {dim}"


def test_skill_md_no_relative_script_calls():
    content = (SKILL_ROOT / "SKILL.md").read_text()
    # Must not contain patterns like "bash scripts/foo.sh" or "python scripts/foo.py"
    assert not re.search(r"\b(bash|python|node)\s+scripts/", content), (
        "SKILL.md must not call scripts via relative paths"
    )
```

- [ ] **Step 3: Run tests to verify they all fail (files don't exist yet)**

```bash
cd /home/bruce/Projects/oh-my-superpowers
uv run pytest skills/agent-review/tests/test_static.py -v 2>&1 | head -40
```

Expected: Multiple FAILED — `SKILL.md`, `references/README.md`, etc. not found.

- [ ] **Step 4: Commit**

```bash
git add skills/agent-review/tests/test_static.py
git commit -m "test: add T1 static checks for agent-review skill"
```

---

## Task 2: Write `references/agent-spec.md`

**Files:**
- Create: `skills/agent-review/references/agent-spec.md`

- [ ] **Step 1: Create the spec file**

```markdown
# Pi Agent Spec

Purpose: Define the valid format for Pi agent markdown files.
Input:   Used by agent-review during frontmatter compliance checks.

---

## File Format

A Pi agent file is a single markdown file with YAML frontmatter followed by a system prompt.

```markdown
---
name: agent-name
description: >-
  One-line description of what this agent does.
tools: read, bash
model: claude-sonnet-4-6
---

System prompt starts here...
```

---

## Frontmatter Fields

### `name` (required)

- Type: string
- Rules:
  - Must match the filename without `.md` extension (e.g., file `foo.md` → `name: foo`)
  - 1–64 characters
  - Lowercase letters, digits, hyphens only
  - No leading, trailing, or consecutive hyphens

### `description` (required)

- Type: string (use `>-` for multi-line)
- Rules:
  - Non-empty
  - Under 1024 characters
  - Should describe what the agent does and when to use it
  - Agents are explicitly invoked — description is for human readability, not auto-triggering

### `tools` (required)

- Type: comma-separated string
- Valid values (exhaustive list):

| Tool | Purpose |
|------|---------|
| `read` | Read file contents |
| `bash` | Execute shell commands |
| `edit` | Precise file edits |
| `write` | Create or overwrite files |
| `grep` | Search file contents |
| `find` | Find files by pattern |
| `ls` | List directory contents |
| `subagent` | Spawn a Pi subagent |

- Rules:
  - Only list tools the agent actually uses
  - Minimum necessary tools (principle of least privilege)
  - No tools outside this list are valid

### `model` (required)

- Type: string
- Recommended values:

| Model ID | Use case |
|----------|----------|
| `claude-sonnet-4-6` | Default — balanced quality and speed |
| `claude-opus-4-6` | Complex reasoning tasks |
| `claude-haiku-4-5-20251001` | Fast, lightweight tasks |

- Other provider/model strings (e.g., `litellm-local/qwen3.5-27b`) are valid but non-standard.

---

## System Prompt

Everything after the closing `---` frontmatter delimiter is the system prompt. No required format, but see `rubric.md` for quality standards.
```

- [ ] **Step 2: Run the tools-list test to verify it passes**

```bash
cd /home/bruce/Projects/oh-my-superpowers
uv run pytest skills/agent-review/tests/test_static.py::test_agent_spec_exists skills/agent-review/tests/test_static.py::test_agent_spec_has_tools_list -v
```

Expected: 2 PASSED.

- [ ] **Step 3: Commit**

```bash
git add skills/agent-review/references/agent-spec.md
git commit -m "docs: add Pi agent spec reference for agent-review"
```

---

## Task 3: Write `references/rubric.md`

**Files:**
- Create: `skills/agent-review/references/rubric.md`

- [ ] **Step 1: Create the rubric file**

```markdown
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
```

- [ ] **Step 2: Run the rubric dimension test**

```bash
cd /home/bruce/Projects/oh-my-superpowers
uv run pytest skills/agent-review/tests/test_static.py::test_rubric_exists skills/agent-review/tests/test_static.py::test_rubric_covers_all_dimensions -v
```

Expected: 2 PASSED.

- [ ] **Step 3: Commit**

```bash
git add skills/agent-review/references/rubric.md
git commit -m "docs: add 8-dimension quality rubric for agent-review"
```

---

## Task 4: Write `references/README.md`

**Files:**
- Create: `skills/agent-review/references/README.md`

- [ ] **Step 1: Create the index file**

```markdown
# agent-review References

Index of reference files. Load only what the active review step requires.

| Scenario | File |
|----------|------|
| Checking frontmatter field rules, valid tools, valid models | `agent-spec.md` |
| Evaluating system prompt quality across 8 dimensions | `rubric.md` |
```

- [ ] **Step 2: Run the README test**

```bash
cd /home/bruce/Projects/oh-my-superpowers
uv run pytest skills/agent-review/tests/test_static.py::test_references_readme_exists -v
```

Expected: 1 PASSED.

- [ ] **Step 3: Commit**

```bash
git add skills/agent-review/references/README.md
git commit -m "docs: add references index for agent-review"
```

---

## Task 5: Write `SKILL.md`

**Files:**
- Create: `skills/agent-review/SKILL.md`

- [ ] **Step 1: Create SKILL.md**

```markdown
---
name: agent-review
description: >-
  Review and audit a Pi agent markdown file for spec compliance and design quality.
  Use when: reviewing an agent file, checking if an agent is ready to deploy,
  auditing agent description or system prompt quality.
  Do NOT use when: reviewing a skill directory (use skill-review), designing a new
  agent (use agent-brainstorming), or testing agent runtime behavior.
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

```markdown
## agent-review: <filename>
Found: X critical, Y warnings, Z suggestions.
Dimensions evaluated: 8 / 8
```

Use this format for each finding:

```markdown
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

If a dimension has no issues, include a one-line pass note in the summary — do not omit it.

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
```

- [ ] **Step 2: Run all remaining T1 tests**

```bash
cd /home/bruce/Projects/oh-my-superpowers
uv run pytest skills/agent-review/tests/test_static.py -v
```

Expected: All 8 tests PASSED.

- [ ] **Step 3: Commit**

```bash
git add skills/agent-review/SKILL.md
git commit -m "feat: add agent-review skill (Reviewer pattern, 8 dimensions)"
```

---

## Task 6: Smoke test against the existing agent

**No new files.** Validate the skill works on `agents/skill-review.md`.

- [ ] **Step 1: Run a quick manual review**

Open a new pi session and invoke agent-review on the existing agent:

```bash
pi --skill skills/agent-review -p "review agents/skill-review.md"
```

- [ ] **Step 2: Verify report structure**

Check the output contains:
- Summary block with `## agent-review: skill-review.md`
- `Dimensions evaluated: 8 / 8`
- At least one finding with Evidence and Suggested fix

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add skills/agent-review/
git commit -m "fix: address smoke test findings in agent-review skill"
```

---

## Summary

| Task | Files | Tests |
|------|-------|-------|
| 1. Bootstrap | `tests/test_static.py` | All T1 tests written (failing) |
| 2. agent-spec.md | `references/agent-spec.md` | 2 tests pass |
| 3. rubric.md | `references/rubric.md` | 2 tests pass |
| 4. README.md | `references/README.md` | 1 test passes |
| 5. SKILL.md | `SKILL.md` | All 8 T1 tests pass |
| 6. Smoke test | — | Manual validation |
