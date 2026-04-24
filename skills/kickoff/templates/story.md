# Story: <story-name>

<!--
Directory naming: stories/<YYYY-MM-DD>-<slug>/
Task breakdown lives in tasks.yaml (single source of truth for state).
This file is narrative only — goal, context, scope, exploration.
Execution Mode is decided per task at dispatch time (see SKILL.md ## Execution Mode).
-->

## Goal

<!-- What the user wants to achieve (not how). One paragraph. -->

## Context

<!-- Links to design docs, related code, prior decisions. -->

- Related code: `<path>`

## Scope

**In scope:**
- <deliverable 1>
- <deliverable 2>

**Out of scope:**
- <explicit exclusion>

## Explore Result

<!-- Phase 2 输出。预判 + cheap grep / 大范围 sub-agent 探索的结论合并到这里。 -->

| No | Files | Functions | Estimation (LOC) |
|:---|:---|:---|:---|
| 1  | models.py | create_model / delete_model | 200 |

**Totals:** files=<N>, est_loc=<N>  ← 用于 Phase 3 wave 切分

## Tasks

See `tasks.yaml` for the task list, status, dependencies, and per-wave snapshots.
