---
name: debug
description: >-
  Systematic debugging for failing tests, runtime errors, and unexpected
  behavior. Use when you can reproduce a bug and need to find the root cause
  with logs and targeted inspection. Do NOT use for feature design, task
  orchestration, or speculative rewrites.
---

# Debug

Use this skill when behavior is wrong and the next step is investigation, not
feature work.

<HARD-GATE>
Do NOT guess, rewrite broadly, or "try a few fixes" before collecting
evidence. Reproducible debugging starts with observation.
</HARD-GATE>

## Checklist

1. **Reproduce the problem** — identify the failing test, command, or user flow.
2. **Read the coding constraints** — load `references/coding-guideline.md`.
3. **Read the debugging method** — load `references/debugging-guideline.md`.
4. **List possible causes** — write 3-7 falsifiable hypotheses before changing code.
5. **Add targeted diagnostics** — log values at decision points, not generic traces.
6. **Read the evidence** — run the failing path and inspect logs, errors, and outputs.
7. **Narrow the scope** — isolate the specific file, function, or condition causing the failure.
8. **Make the smallest fix** — change only what addresses the root cause.
9. **Verify** — rerun the original failing test or reproduction, then related checks.
10. **Clean up** — remove temporary logs and debugging artifacts.

## Loading Guide

Load only what you need:

- `references/coding-guideline.md`
  Use before editing code so the fix stays simple, surgical, and goal-driven.

- `references/debugging-guideline.md`
  Use when a test fails, runtime behavior is wrong, or the cause is unclear.

## Boundaries

- This skill is for debugging and root-cause analysis.
- This skill does not do task orchestration, story breakdown, or agent routing.
- This skill does not justify speculative refactors or unrelated cleanup.
