# Openclaw Browser Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable `openclaw-browser` skill that teaches OpenClaw CLI browser workflows with clear guardrails and minimal context cost.

**Architecture:** Keep the execution workflow in `SKILL.md` and move command details and examples into three reference files. Treat this as documentation-first implementation with lightweight validation rather than code-heavy automation.

**Tech Stack:** Markdown, YAML frontmatter, OpenClaw CLI command conventions, local repo skill conventions

---

### Task 1: Create the design and implementation docs

**Files:**
- Create: `docs/plans/2026-03-11-openclaw-browser-design.md`
- Create: `docs/plans/2026-03-11-openclaw-browser-impl.md`

**Step 1: Write the documentation content**

Add the approved design, boundaries, workflow, guardrails, and the implementation tasks in the two plan files.

**Step 2: Verify the files render cleanly**

Run: `sed -n '1,80p' docs/plans/2026-03-11-openclaw-browser-design.md`
Expected: header explains purpose, input/output, and major sections within the first 20 lines.

**Step 3: Commit**

```bash
git add docs/plans/2026-03-11-openclaw-browser-design.md docs/plans/2026-03-11-openclaw-browser-impl.md
git commit -m "docs: add openclaw-browser design and implementation plans"
```

### Task 2: Create the skill entry point

**Files:**
- Create: `skills/openclaw-browser/SKILL.md`

**Step 1: Write the skill frontmatter and summary header**

Describe the skill as a general OpenClaw browser workflow guide. Make the description trigger on reading pages, clicking, filling forms, screenshots, debugging, and browser environment simulation.

**Step 2: Write the main workflow**

Include:
- prerequisite check
- task classification
- snapshot-first interaction rule
- wait and verify loop
- completion criteria

**Step 3: Add hard guardrails**

Include explicit constraints for:
- no ref action before snapshot
- no JS evaluation unless necessary
- re-snapshot after DOM changes
- prefer evidence and JSON output

**Step 4: Review for context discipline**

Expected: command details are linked to references, not duplicated in `SKILL.md`.

### Task 3: Add focused references

**Files:**
- Create: `skills/openclaw-browser/references/cli-cheatsheet.md`
- Create: `skills/openclaw-browser/references/workflow-patterns.md`
- Create: `skills/openclaw-browser/references/safety-and-debugging.md`

**Step 1: Write the cheatsheet**

Document minimal commands for:
- status/start/profiles
- open/navigate/tabs/focus/close
- snapshot/click/type/fill/select/drag
- wait/evaluate
- screenshot/pdf/console/requests/errors
- set device/timezone/geo/headers/media/viewport/offline

**Step 2: Write workflow patterns**

Document concise multi-step flows for:
- read a page
- interact with a form
- handle SPA changes
- collect debugging evidence
- emulate an environment

**Step 3: Write safety and debugging guidance**

Document:
- when to use `--json`
- when to avoid `--fn`
- how to recover from stale refs
- how to work with `target-id` and profiles

**Step 4: Review for overlap**

Expected: each file has a distinct role and no large duplicated examples.

### Task 4: Validate the skill structure

**Files:**
- Test: `skills/openclaw-browser/SKILL.md`
- Test: `skills/openclaw-browser/references/cli-cheatsheet.md`
- Test: `skills/openclaw-browser/references/workflow-patterns.md`
- Test: `skills/openclaw-browser/references/safety-and-debugging.md`

**Step 1: Verify the file tree**

Run: `find skills/openclaw-browser -maxdepth 2 -type f | sort`
Expected: only the planned four files exist.

**Step 2: Verify headers**

Run: `sed -n '1,40p' skills/openclaw-browser/SKILL.md`
Expected: frontmatter plus a summary block that explains purpose, input, output, and sections.

**Step 3: Run a lightweight syntax sanity check**

Run: `python - <<'PY'\nfrom pathlib import Path\nfor path in Path('skills/openclaw-browser').rglob('*.md'):\n    text = path.read_text()\n    assert text.strip(), path\nprint('ok')\nPY`
Expected: `ok`

**Step 4: Commit**

```bash
git add skills/openclaw-browser
git commit -m "feat(skills): add openclaw-browser skill"
```
