---
name: skill-review
description: >-
  Review, audit, and improve an Agent Skill for specification compliance,
  instruction quality, trigger quality, script design, and eval readiness.
  Use when reviewing a skill directory, checking a SKILL.md file, auditing
  skill references or scripts, diagnosing why a skill triggers poorly, or
  evaluating whether a skill is ready to deploy.
---

# Skill Review

Purpose: Audit a skill directory for issues in spec compliance, design quality, and evidence quality.
Input:   Skill directory path from user. Optional audit mode: quick | full | trigger-audit | eval-audit.
Output:  Diagnostic report grouped by severity, with evidence, rationale, concrete fixes, and verification steps.
Sections: Prerequisite Check | Workflow | Output Format | Done Criteria | Guardrails

## Prerequisite Check

If the skill directory path is not provided, ask before proceeding:

> Which skill directory should I review? Please provide the path.
> Example: `skills/my-skill` or `/home/user/.claude/skills/my-skill`

Verify `SKILL.md` exists inside the directory. If it does not, stop and report.

## Workflow

### Phase 0: Select Audit Mode

- Default to `quick` if the user does not specify a mode.
- Use `full` only when the user asks for a full audit or deployment readiness review.
- Use `trigger-audit` when the user asks about triggering, description quality, false positives, or false negatives.
- Use `eval-audit` when the user asks whether the skill has enough testing, evidence, or evaluation assets.

### Phase 1: Mechanical Checks (script)

```bash
python scripts/consistency_check.py --skill-dir <path>
```

The script reports mechanical issues the LLM must not reinvent:
- **Parameter mismatch**: a `--flag` in SKILL.md does not appear in the script's `--help` output.
- **Missing file**: a path referenced in SKILL.md (`references/`, `assets/`, `scripts/`) does not exist on disk.
- **Name mismatch**: the `name` field in YAML frontmatter does not match the directory name.
- **Legacy pollution**: commented-out code blocks or migration TODOs in scripts/.
- **Spec violations**: malformed frontmatter, invalid `name`, oversize `description`, or force-load syntax.
- **Reference hygiene**: orphaned references and path-style violations.

Incorporate all script findings into the final report before writing any LLM observations.

### Phase 2: Load Core Review Instructions

Always read:
- The target skill's `SKILL.md`
- `references/rubric.md`

Do NOT read every file in the target skill by default.
Load support files progressively, only when the active audit mode requires them.

### Phase 3: Progressive Disclosure Review

Load additional files only when needed:

- For `quick`: inspect the target `SKILL.md`, then inspect only the scripts and references directly cited by findings or by the workflow.
- For `full`: inspect the target `SKILL.md`, all scripts under `scripts/`, and all linked files under `references/`. Read unlinked references only if Phase 1 reports them as orphaned.
- For `trigger-audit`: read `references/how-to-optimize-skill-descriptions.md`, then focus on frontmatter, trigger boundaries, near-miss ambiguity, and overlap with adjacent skills.
- For `eval-audit`: read `references/how-to-evaluate-skill-output-quality.md`, then inspect `evals/`, benchmarks, assertions, or any evidence files if present.
- When reviewing script design, read `references/how-to-use-scripts-in-skills.md`.
- When validating spec constraints, read `references/agent-skills-spec.md`.
- When reviewing structure and calibration, read `references/agent-skills-best-practices.md`.

### Phase 4: Layered Semantic Review

Evaluate findings by layer:

1. **Spec Compliance**
   Check spec-level requirements and path discipline. Prefer Phase 1 evidence when available.
2. **Design Quality**
   Check description quality, workflow structure, progressive disclosure, guardrails, output templates, and script interface design.
3. **Evidence Quality**
   Check whether the skill provides credible trigger evals, output evals, baselines, assertions, or iteration evidence.

Use these labels on every finding:
- `SPEC`
- `BEST_PRACTICE`
- `PROJECT_POLICY`

Do NOT label a project preference as spec.

## Output Format

Write the review report in the user's language.
If the user mixes languages, follow the dominant language of the request.
Do NOT force the report to English unless the user is clearly writing in English.

Start the report with this summary block:

```markdown
## skill-review: <skill-name>
Mode: <mode>
Found: X critical, Y warnings, Z suggestions.
Coverage:
- Spec Compliance: complete | partial | skipped
- Design Quality: complete | partial | skipped
- Evidence Quality: complete | partial | skipped
```

Use this format for each issue:

```markdown
### [SEVERITY] <Layer> / <Dimension Name>

Labels: SPEC | BEST_PRACTICE | PROJECT_POLICY

**Issue:** One sentence describing the problem precisely.

**Evidence:**
<exact quote from a file, concrete file state, or script JSON entry>

**Why it matters:**
<one sentence on execution, trigger accuracy, output quality, or maintainability>

**Suggested fix:**
<concrete replacement text or specific action>

**How to verify:**
<specific follow-up check, command, or expected file state>
```

Severity levels:
- `[CRITICAL]` — prevents correct execution or correct triggering
- `[WARNING]` — degrades reliability or output quality
- `[SUGGESTION]` — improvement opportunity

Group all findings by severity: CRITICAL first, then WARNING, then SUGGESTION.

## Failure Handling

- If `consistency_check.py` fails to execute: report the error verbatim, skip Phase 1, proceed to the semantic review, and note in the report that mechanical checks were not performed.
- If `references/rubric.md` cannot be read: stop and report the missing file. Do not continue without the rubric.
- If a mode-specific reference file cannot be read: continue the audit, but mark that layer as partial coverage.

## Done Criteria

- Phase 1 script has run and all findings are incorporated, unless script execution failed and that failure is reported.
- Every dimension required by the selected mode has been evaluated.
- Every issue has evidence, a concrete fix, and a verification step.
- The report language follows the user's language.
- Report starts with the summary block and includes correct coverage states.

## Guardrails

NO finding WITHOUT a direct quote from a file, a concrete file state, or an entry in the script's JSON output.
No exceptions. If you cannot point to a specific source, do not report it.

- Ground every finding in the exact quote, file state, or JSON key that proves the issue.
- Do NOT invent issues. Every finding must cite a specific source.
- Do NOT load the entire skill directory unless the active mode requires it.
- Do NOT skip required dimensions because the skill "looks fine". Evaluate all dimensions required by the active mode.
- Do NOT merge multiple distinct issues into one entry. One entry per issue.
- Do NOT call a project preference a spec violation. Use labels correctly.
