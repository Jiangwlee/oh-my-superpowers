# Skill Review Rubric

Purpose: Define detailed evaluation criteria for the 12 skill quality dimensions.
Input:   Called by the LLM during Phase 2 of skill-review.
Output:  (reference only — no output produced by this file)
Sections: Dimensions 1–12 | Severity Guide

---

## Dimension 1: description Trigger Formula

**Criteria**

The `description` field must follow this formula:
```
[Capability overview] + "Use when" + [(1) scenario (2) scenario ...]
```

Both parts are required. The trigger list must cover multiple phrasing styles:
declarative ("convert markdown"), interrogative ("how do I export"), imperative ("export this").

**Common violations**

| Violation | Example |
|-----------|---------|
| Only capability, no trigger | `description: Converts markdown to images.` |
| Workflow summary instead of trigger | `description: Fetches data, runs analysis, writes report.` |
| Trigger only, no capability | `description: Use when user says "review".` |
| Single trigger phrase, narrow coverage | `Use when user says "export to PDF"` |

**CSO trap**: If description summarises the workflow, the LLM may follow the description
and skip reading the body. The body becomes dead documentation.

**Severity**: CRITICAL if trigger section is absent or is a workflow summary.

---

## Dimension 2: YAML Compliance

**Criteria**

| Field | Rule |
|-------|------|
| `name` | kebab-case, lowercase only, no spaces, no underscores |
| `name` | Must not start with `claude` or `anthropic` |
| `description` | Under 1024 characters total |
| `description` | No XML angle brackets (`<` or `>`) |
| Frontmatter delimiters | Must open and close with `---` |

**Common violations**

- `name: My Cool Skill` — spaces and capitals
- `name: my_skill` — underscores
- Description contains `<br>` or `<code>` tags
- Missing closing `---` delimiter

**Severity**: CRITICAL for name format or missing delimiters; WARNING for description length.

---

## Dimension 3: Prerequisite Check

**Criteria**

The skill must have a `## Prerequisite Check` section that:
1. Lists all external tools, credentials, or data required before execution.
2. Provides detection commands (e.g., `command -v node`, `gh auth status`).
3. Explicitly instructs the agent to **stop** if any prerequisite fails — not to continue.

**Common violations**

- Prerequisite check section is absent entirely.
- Section exists but has no detection commands — just prose warnings.
- Section says "ensure X is installed" without saying what to do if it is not.

**Severity**: WARNING if section is absent; SUGGESTION if detection commands are missing.

---

## Dimension 4: Hard Constraints (Iron Law / HARD-GATE)

**Criteria**

Critical rules that cannot be bypassed must use one or both patterns:

**Iron Law format:**
```
NO <prohibited action> WITHOUT <required prerequisite> FIRST.
No exceptions.
```

**HARD-GATE tag:**
```
<HARD-GATE>
<constraint content>
</HARD-GATE>
```

Authority-level language must accompany hard constraints: `YOU MUST`, `ALWAYS`, `NEVER`,
`No exceptions`.

**Common violations**

- Critical rules written as polite suggestions: "please make sure to validate…"
- Iron Law present but missing "No exceptions" clause, leaving a loophole.
- Constraint buried in prose rather than in a dedicated section or tag.

**Severity**: CRITICAL if a constraint that can break the workflow uses soft language.

---

## Dimension 5: Token Cost Control

**Criteria**

| Skill type | SKILL.md body target |
|------------|---------------------|
| Getting-started / entry | < 150 words |
| Frequently loaded | < 200 words |
| Other | < 500 words; hard limit 500 lines |

- Large reference material (API docs, examples > 100 lines) must live in `references/`.
- `@path/to/file` syntax must not appear — it force-loads files immediately.
- Cross-skill references must use `REQUIRED SUB-SKILL: Use <skill-name>` pattern.

**Common violations**

- Inline API documentation that belongs in `references/`.
- `@skills/xxx/SKILL.md` link that burns 200k+ context before needed.
- Repeated instructions that duplicate content from another skill.

**Severity**: WARNING if body exceeds 500 lines; SUGGESTION for `@` syntax.

---

## Dimension 6: Workflow Structure

**Criteria**

Every step-based workflow must contain all three elements:

1. **Numbered steps** — unambiguous execution order.
2. **Done Criteria** — explicit definition of what "complete" means for each step and overall.
3. **Failure Handling** — explicit instruction for each failure mode: what to report, whether to stop or retry.

**Common violations**

- Steps are numbered but Done Criteria section is absent.
- Failure Handling says "handle errors" without specifying stop vs retry vs escalate.
- Workflow sections exist but steps are unnumbered, allowing arbitrary reordering.

**Severity**: WARNING for missing Done Criteria or Failure Handling.

---

## Dimension 7: Output Format Specification

**Criteria**

The skill must declare one of two output modes and honour it consistently:

- **Strict template**: `ALWAYS use this exact template`. Provide the template verbatim.
- **Flexible guidance**: `Here is a default; use judgment`. Provide a sensible default.

Input/Output examples are required when output format is non-obvious.

**Common violations**

- No output format declared — the LLM free-styles every time.
- Template declared but not provided ("output a JSON object").
- Multiple output formats described without a decision rule for which to use.

**Severity**: WARNING if no format is declared for structured output; SUGGESTION otherwise.

---

## Dimension 8: File Reference Style

**Criteria**

| Pattern | Rule |
|---------|------|
| Script invocation | `python scripts/foo.py` — relative path only |
| Script invocation | Never `python $SKILL_DIR/scripts/foo.py` |
| Config file access | Script uses `pathlib.Path(__file__).resolve().parent` to self-locate |
| Cross-skill reference | `REQUIRED SUB-SKILL: Use <skill-name>` |
| Cross-skill reference | Never `@skills/xxx/SKILL.md` |
| Conditional reference | State the condition: "If X, read references/x.md" |

**Common violations**

- `python3 $SKILL_DIR/scripts/foo.py` — environment variable path prefix.
- `@skills/testing/SKILL.md` — force-load syntax.
- `references/api.md` referenced without a loading condition, causing default load.

**Severity**: WARNING for `$SKILL_DIR` usage or `@` syntax.

---

## Dimension 9: LLM Behaviour Control (Guardrails)

**Criteria**

The skill must have a `## Guardrails` section (or equivalent) that:
- Uses authority language: `YOU MUST`, `Do NOT`, `NEVER`, `Always`, `No exceptions`.
- Lists the most likely failure modes for that specific skill.
- Mixes positive rules (what to do) and negative rules (what not to do).

**Common violations**

- Guardrails section is absent.
- Rules use hedging language: "try to avoid", "it is recommended that".
- Only negative rules — no positive anchors to correct behaviour.
- Generic rules copied from a template that do not address this skill's failure modes.

**Severity**: WARNING if section is absent; SUGGESTION for weak language.

---

## Dimension 10: Consistency (Script Results)

**Criteria**

This dimension is populated exclusively from `consistency_check.py` output.
The LLM must not invent findings here — only report what the script detected.

Three categories:

| Category | What it means |
|----------|---------------|
| `parameter_mismatches` | A `--flag` in SKILL.md does not appear in the script's `--help` |
| `missing_files` | A path in SKILL.md (`references/`, `assets/`, `scripts/`) does not exist |
| `name_mismatch` | `name` in frontmatter differs from the directory name |

**Severity**: CRITICAL for parameter mismatches (silent runtime failure); WARNING for missing
files; WARNING for name mismatch.

---

## Dimension 11: Language and Writing Quality

**Criteria**

All documentation in the skill (SKILL.md, references/, scripts docstrings) must meet
all four standards:

| Standard | Rule |
|----------|------|
| Language | English throughout. Chinese only for user-facing trigger phrases. |
| Grammar | Correct English grammar. Subject–verb agreement, proper tense. |
| Precision | No ambiguous verbs. Use `parse`, `validate`, `write to` not `handle`, `process`, `do`. |
| Self-containment | No assumed context. No "as mentioned above", "previously", "like before". |
| No compatibility prose | No "for backward compatibility", "previously this was X", migration notes. |

**Common violations**

- Chinese prose mixed into workflow steps.
- Ambiguous verb: "handle errors" (handle how? stop? retry? log?).
- Context-dependent reference: "use the same format as above".
- Compatibility note: "this replaces the old `--input` flag".
- Stale comments: "// 旧版兼容" or "# TODO: remove after migration".

**Severity**: WARNING for non-English prose in instructions; SUGGESTION for precision issues.

---

## Dimension 12: Legacy Pollution (Dead Content)

**Criteria**

Skills accumulate stale content across upgrades. Detect three categories:

**Category A — Dead steps in SKILL.md**
Workflow steps or sections that reference scripts, flags, files, or behaviours that no
longer exist or are no longer reachable in any execution path.

Signals:
- A step references a script not present in `scripts/`.
- A step describes a flag or parameter that Phase 1 reported as mismatched.
- A conditional branch references a file or mode that does not exist.
- An entire section (e.g., an old workflow variant) is never reached from any trigger.

**Category B — Dead code in scripts/**
Stale artefacts inside Python or shell scripts:
- Commented-out code blocks (more than one consecutive commented line of logic).
- Functions defined but never called within the skill's execution paths.
- Imports that are never used.
- `# TODO: remove`, `# FIXME: migrate`, `# legacy`, or `# compat` comments.

The script `consistency_check.py` reports commented-out blocks and migration TODOs.
Use those findings as input. LLM must also read scripts and apply judgment.

**Category C — Dead documentation in references/**
Reference files that describe features, parameters, or workflows that have been removed
from SKILL.md or from the underlying scripts.

Signals:
- A section in a reference file describes a `--flag` that no longer exists in any script.
- A reference file is no longer linked from SKILL.md (orphaned file).
- A reference file documents a workflow path that was deleted from SKILL.md.

**Common violations**

| Location | Example |
|----------|---------|
| SKILL.md | Step 4 calls `scripts/validate_output.py` which was deleted two versions ago |
| scripts/ | 30 lines of commented-out argparse block from a refactor |
| scripts/ | `import csv` at top; csv is never used after data format changed |
| references/ | `references/legacy-format.md` describes JSON v1 format; skill now only uses v2 |
| references/ | `references/old-workflow.md` exists but is not referenced anywhere in SKILL.md |

**How to detect**

1. Cross-reference all script calls in SKILL.md against `scripts/` directory contents.
2. Read each script: flag commented blocks (>1 line), unused imports, TODO/compat comments.
3. List all `references/` files. For each, check whether SKILL.md links to it.
4. For each linked reference file, check whether its described features still exist.

**Severity**: CRITICAL if a dead step will cause runtime failure; WARNING for dead code
blocks or orphaned reference files; SUGGESTION for single commented lines or stale TODOs.

---

## Severity Guide

| Level | Definition |
|-------|------------|
| `[CRITICAL]` | The skill will fail to execute correctly or fail to trigger. Fix before deploying. |
| `[WARNING]` | The skill will work but produce unreliable or low-quality results. Fix soon. |
| `[SUGGESTION]` | The skill works correctly but has room for improvement. Fix opportunistically. |
