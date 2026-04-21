# Story: <story-name>

Mode: <inline | multi_wave>

<!--
Directory naming: stories/<YYYY-MM-DD>-<slug>/
Task breakdown lives in tasks.yaml (single source of truth for state).
This file is narrative only — goal, context, scope, exploration.
Mode is set in Phase 1 step 6 and never edited mid-story.
-->

## Goal

<!-- What the user wants to achieve (not how). One paragraph. -->

## Context

<!-- Links to design docs, related code, prior decisions. -->

- Design: `docs/brainstorming/specs/YYYY-MM-DD-<slug>.md`
- Related code: `<path>`

## Scope

**In scope:**
- <deliverable 1>
- <deliverable 2>

**Out of scope:**
- <explicit exclusion>

## Explore Result

<!-- Phase 1 step 4 输出。内联 Grep/Glob 的结果。-->

| No | Files | Functions | Estimation (LOC) |
|:---|:---|:---|:---|
| 1  | models.py | create_model / delete_model | 200 |

**Totals:** files=<N>, est_loc=<N>  ← 用于 Mode Decision

## Tasks

See `tasks.yaml` for the task list, status, and dependencies.
