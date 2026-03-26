# Skill Review Rubric

Purpose: Define layered evaluation criteria for skill-review v2.
Input:   Called by the LLM during semantic review.
Output:  Reference only. This file defines layers, dimensions, labels, and severity guidance.
Sections: Layer A | Layer B | Layer C | Label Rules | Severity Guide

---

## Layer A: Spec Compliance

These dimensions answer: does the skill conform to the Agent Skills spec and to path-level execution rules?

### A1. Frontmatter and Directory Spec

**Labels**
- `SPEC`

**Criteria**

Check:
- `SKILL.md` exists and uses valid opening and closing `---` delimiters.
- `name` matches the parent directory name.
- `name` is 1-64 characters, lowercase, hyphenated, and has no leading, trailing, or consecutive hyphens.
- `description` exists, is non-empty, and is under 1024 characters.
- Optional spec fields such as `license`, `compatibility`, `metadata`, and `allowed-tools` are structurally valid if present.

Prefer script output for mechanical violations.

**Severity**
- CRITICAL for malformed frontmatter, invalid `name`, or missing `description`
- WARNING for optional-field misuse that does not block activation

### A2. File Reference Discipline

**Labels**
- `SPEC`
- `BEST_PRACTICE`

**Criteria**

Check:
- Script invocations use relative paths such as `python scripts/foo.py`.
- The skill does not use path variables such as `$SKILL_DIR` to invoke its own files.
- Cross-skill references do not use force-load syntax such as `@skills/foo/SKILL.md`.
- Referenced files exist.
- References are introduced with loading conditions when they are not always needed.

Prefer script output for missing files, force-load syntax, and path-style violations.

**Severity**
- CRITICAL when a bad path or missing file will cause runtime failure
- WARNING for unstable reference style or unconditional large-file loading

### A3. Mechanical Consistency

**Labels**
- `SPEC`
- `PROJECT_POLICY`

**Criteria**

This dimension is populated primarily from `consistency_check.py`.
Use script findings for:
- parameter mismatches
- missing files
- name mismatch
- frontmatter errors
- description length violations
- orphaned references
- legacy pollution

Do not invent a finding here if the script produced no evidence.

**Severity**
- CRITICAL for parameter mismatches
- WARNING for missing files, name mismatch, orphaned references, or stale script content

## Layer B: Design Quality

These dimensions answer: is the skill written in a way that helps an agent succeed reliably and efficiently?

### B1. Trigger Description Quality

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

The `description` should:
- describe both capability and when to use it
- focus on user intent, not workflow internals
- avoid becoming a workflow summary
- cover realistic wording breadth, including near-miss phrasing where relevant

Use `references/how-to-optimize-skill-descriptions.md` when trigger quality is in scope.

**Severity**
- CRITICAL if the description is so narrow or malformed that triggering is likely to fail
- WARNING if the description is vague, over-broad, or likely to false-trigger

### B2. Progressive Disclosure and Context Cost

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

Check:
- `SKILL.md` contains only the core workflow and constraints needed on every run
- large examples and long reference material live in `references/`
- the skill avoids `@path` force-load syntax
- the skill tells the agent when to load each reference file

**Severity**
- WARNING when the body is bloated or references are always-on without need
- SUGGESTION when structure works but can be tighter

### B3. Workflow Structure and Failure Handling

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

For multi-step tasks, check:
- clear execution order
- explicit completion conditions
- explicit failure handling
- coherent scope rather than an over-broad menu of unrelated tasks

**Severity**
- WARNING when missing done criteria or failure handling degrades reliability
- SUGGESTION when the workflow works but is harder to follow than necessary

### B4. Guardrails and Hard Constraints

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

Check:
- likely failure modes are called out explicitly
- critical constraints use strong language
- the skill mixes positive anchors and negative prohibitions
- hard constraints are not buried in soft prose

**Severity**
- CRITICAL when a fragile workflow relies on soft or optional language
- WARNING when guardrails exist but are generic or weak

### B5. Script Interface Design

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

When `scripts/` directory exists, check these hard constraints first:

**Hard constraints (PROJECT_POLICY):**
- The skill has exactly one CLI entry point named `omp-<skill-name>` under `scripts/`
- `SKILL.md` invokes the CLI by name (`omp-<skill-name> ...`), not by relative path (`bash scripts/...` or `python scripts/...`)
- There are no additional standalone scripts that bypass the CLI

**Design quality (BEST_PRACTICE):**
- Complex shell logic is pushed into the CLI rather than inlined in SKILL.md
- Prerequisites (runtime version, PATH requirements) are stated clearly
- CLI usage shown in SKILL.md matches the actual CLI interface (`--help` output)

Use `references/how-to-use-scripts-in-skills.md` when script design is in scope.

**Severity**
- CRITICAL when `scripts/` exists but no `omp-<skill-name>` CLI is present
- CRITICAL when `SKILL.md` invokes scripts via relative path (`bash scripts/` or `python scripts/`)
- CRITICAL when more than one CLI entry point exists under `scripts/`
- WARNING when CLI prerequisites are unstated or CLI usage drifts from `--help`
- SUGGESTION when script usage is correct but not well-calibrated

### B6. Output Contract Quality

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

Check:
- the expected output shape is clear
- strict templates include the actual template
- flexible output guidance still provides a sensible default
- examples exist when the output is non-obvious

**Severity**
- WARNING when the output contract is underspecified for a structured task
- SUGGESTION when output guidance exists but lacks polish

### B7. Writing Quality and Dead Documentation

**Labels**
- `BEST_PRACTICE`
- `PROJECT_POLICY`

**Criteria**

Check:
- precise verbs
- self-contained wording
- no migration prose or compatibility notes
- no stale workflow branch, stale reference, or dead documentation that no longer maps to the current skill

Use script findings as anchors, then extend with semantic judgment only when you can cite the exact stale content.

**Severity**
- WARNING for dead documentation or non-English operational prose that harms reliability
- SUGGESTION for wording precision issues

## Layer C: Evidence Quality

These dimensions answer: is there evidence that the skill triggers well and produces good outputs?

### C1. Eval Readiness

**Labels**
- `BEST_PRACTICE`

**Criteria**

Check whether the skill includes any evaluation assets such as:
- `evals/`
- prompt cases
- expected outputs
- assertions
- benchmark or grading files

If the skill claims production readiness but has no evaluation assets, call that out.

**Severity**
- WARNING when a complex or deployment-bound skill has no evaluation assets
- SUGGESTION when basic eval assets exist but are incomplete

### C2. Trigger Evidence

**Labels**
- `BEST_PRACTICE`

**Criteria**

If trigger evaluation assets exist, check:
- both should-trigger and should-not-trigger cases exist
- near-miss negatives are represented
- train and validation separation exists where optimization is claimed
- trigger behavior is supported by evidence, not assertion

Use `references/how-to-optimize-skill-descriptions.md` when this dimension is in scope.

**Severity**
- WARNING when trigger quality is claimed but unsupported by eval evidence
- SUGGESTION when evidence exists but coverage is shallow

### C3. Output Quality Evidence

**Labels**
- `BEST_PRACTICE`

**Criteria**

If output evaluation assets exist, check:
- realistic prompts
- expected outputs
- assertions with concrete pass/fail criteria
- baseline comparison
- grading or benchmark artifacts

Use `references/how-to-evaluate-skill-output-quality.md` when this dimension is in scope.

**Severity**
- WARNING when output quality is claimed but unsupported by eval evidence
- SUGGESTION when evidence exists but lacks assertions, baselines, or grading discipline

## Label Rules

- Use `SPEC` only for issues grounded in the Agent Skills spec or strict format requirements.
- Use `BEST_PRACTICE` for broadly useful design guidance from the reference set.
- Use `PROJECT_POLICY` for repository-specific style, stricter conventions, or deployment expectations.
- A finding may have more than one label.
- Do not mark a pure project preference as `SPEC`.

## Severity Guide

| Level | Definition |
|-------|------------|
| `[CRITICAL]` | The skill will fail to execute correctly, fail to trigger correctly, or is likely to mislead the agent into a broken path. |
| `[WARNING]` | The skill will probably work, but reliability, output quality, maintainability, or evidence quality is meaningfully degraded. |
| `[SUGGESTION]` | The skill works, but there is a defensible improvement in clarity, efficiency, or calibration. |
