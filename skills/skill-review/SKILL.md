---
name: skill-review
description: >-
  Use when reviewing, auditing, or checking a skill for quality issues.
  Triggers on: "review this skill", "check my SKILL.md", "audit the skill",
  "find problems in this skill", "improve this skill", "is this skill well-written",
  "before deploying a skill".
---

# Skill Review

Purpose: Audit a skill directory for quality issues across 12 dimensions.
Input:   Skill directory path from user.
Output:  Diff-style diagnostic report grouped by severity.
Sections: Prerequisite Check | Workflow | Output Format | Done Criteria | Guardrails

## Prerequisite Check

If the skill directory path is not provided, ask before proceeding:

> Which skill directory should I review? Please provide the path.
> Example: `skills/my-skill` or `/home/user/.claude/skills/my-skill`

Verify `SKILL.md` exists inside the directory. If it does not, stop and report.

## Workflow

### Phase 1: Consistency Check (script)

```bash
python scripts/consistency_check.py --skill-dir <path>
```

The script reports four categories of mechanical issues:
- **Parameter mismatch**: a `--flag` in SKILL.md does not appear in the script's `--help` output.
- **Missing file**: a path referenced in SKILL.md (`references/`, `assets/`) does not exist on disk.
- **Name mismatch**: the `name` field in YAML frontmatter does not match the directory name.
- **Legacy pollution**: commented-out code blocks or migration TODOs in scripts/.

Incorporate all script findings into the final report before writing any LLM observations.

### Phase 2: Semantic Quality Review (LLM)

Read all files in the skill directory.
Read `references/rubric.md` for detailed criteria for each of the 12 dimensions.

Evaluate every dimension. Report every issue found, however minor.

Evaluation priority (most critical first):
1. SKILL.md — description formula, structure, constraints, language quality
2. scripts/ — path reference style, parameter alignment with Phase 1 findings
3. references/ — loading conditions, file existence

## Output Format

Start the report with a one-line summary:

```
## skill-review: <skill-name>
Found: X critical, Y warnings, Z suggestions.
```

Use this format for each issue:

```
### [SEVERITY] Dimension N: <Dimension Name>

**Issue:** One sentence describing the problem precisely.

**Current:**
<exact quote from the file, or "(section missing)" if absent>

**Suggested fix:**
<concrete replacement text or specific action>
```

Severity levels:
- `[CRITICAL]` — prevents correct execution or correct triggering
- `[WARNING]` — degrades reliability or output quality
- `[SUGGESTION]` — improvement opportunity

Group all findings by severity: CRITICAL first, then WARNING, then SUGGESTION.

## Failure Handling

- If `consistency_check.py` fails to execute: report the error verbatim, skip Phase 1,
  proceed to Phase 2, and note in the report that mechanical checks were not performed.
- If `references/rubric.md` cannot be read: stop and report the missing file.
  Do not attempt Phase 2 without the rubric.

## Done Criteria

- Phase 1 script has run and all findings are incorporated.
- All 12 dimensions have been evaluated.
- Every issue has a concrete fix.
- Report starts with the summary line.

## Guardrails

NO finding WITHOUT a direct quote from a file or an entry in the script's JSON output.
No exceptions. If you cannot point to a specific source, do not report it.

- Ground every finding in the exact line or JSON key that proves the issue.
- Do NOT invent issues. Every finding must cite a specific quote or script output.
- Do NOT skip dimensions because the skill "looks fine". Evaluate all 12. No exceptions.
- Do NOT merge multiple distinct issues into one entry. One entry per issue.
