# Story: <story-name>

<!--
Directory: stories/<YYYY-MM-DD>-<slug>/
Task state lives in tasks.yaml (SSOT).
This file is narrative only: goal, context, scope, exploration.
Execution Mode is chosen per task at dispatch time.
-->

## Goal

<!-- 用户想达成什么；描述结果，不描述实现手段。一个自然段即可。 -->

## Context

<!-- 相关设计文档、已有代码、历史决策、依赖路径。 -->

- Related code: `<path>`

## Scope

**In scope**
- <deliverable 1>
- <deliverable 2>

**Out of scope**
- <explicit exclusion>

## Explore Result

<!--
Phase 2 输出。
把 cheap grep 和大范围探索（若由 sub-agent 完成）的结论统一收敛到这里。
-->

| No | Files | Functions | Estimation (LOC) |
|:---|:---|:---|:---|
| 1 | models.py | create_model / delete_model | 200 |

**Totals:** files=<N>, est_loc=<N>

## Tasks

See `tasks.yaml` for task list, status, dependencies, and wave snapshots.
