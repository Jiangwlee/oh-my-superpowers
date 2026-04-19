# Task: seed the fake

## Context

Story: `stories/2026-04-19-fake/story.md`
Design: `/docs/brainstorming/specs/2026-04-19-fake.md`

Minimal fixture task — exists only to let orchestrator prove wave-1 dispatch works.

## Objective

**Do:**
- Create `src/fake/seed.py`

**Do NOT:**
- Touch anything outside `src/fake/`

## Read First

- `src/fake/` — confirm it does not exist yet

## File Scope

- `src/fake/seed.py`

## Workflow

1. Create the file with a placeholder function
2. Done

## Worker Refs

- `references/constitution.md`
- `worker-refs/worker-guideline.md`
- `../story-memory.md`

## Deviation Rules

🟢 None expected.

## Acceptance Criteria

### Must-Haves

**Artifacts:**
- path: `src/fake/seed.py`
  provides: "a placeholder seed function"
  contains: "def seed"

## Test Plan

- [ ] File exists with `def seed` definition
