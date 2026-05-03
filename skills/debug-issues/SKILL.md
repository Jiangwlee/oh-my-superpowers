---
name: debug-issues
description: >-
  Systematic debugging for failing tests, runtime errors, and unexpected
  behavior. Use when investigating bugs, finding root causes, or before
  attempting fixes. Do NOT use for feature design, task orchestration, or
  speculative rewrites.
---

# Debug Issues

Use this skill when behavior is wrong and the next step is investigation.

<HARD-GATE>
Do NOT guess, rewrite broadly, or "try a few fixes" before collecting evidence.
Do NOT read code before the suspect range is narrowed to 1-2 files.
Do NOT skip Phase 1 framing when symptom / repro / expected / actual is incomplete.
</HARD-GATE>

## Workflow

```mermaid
flowchart TD
    P1[1. Frame the problem]
    P1G{Symptom + repro + expected + actual present?}
    P1A[Ask 3-5 focused questions]
    P2[2. Reproduce the failure]
    P3[3. Scope triage<br/>layer / ownership / side]
    P4[4. List 3-7 falsifiable hypotheses<br/>constrained by scope]
    P5[5. Observe and narrow<br/>browser / logs / curl / read]
    P5G{Suspect range narrowed<br/>to 1-2 files?}
    P6[6. Read code, find root cause,<br/>apply smallest fix]
    P7[7. Verify: rerun failing path<br/>+ related checks]
    P7G{Original failure gone?}
    P8[8. Clean up diagnostics]
    P8G{Worth persisting?}
    P9[9. Write docs/debug/&lt;symptom&gt;.md]
    DONE([Done])

    P1 --> P1G
    P1G -- no --> P1A --> P1
    P1G -- yes --> P2 --> P3 --> P4 --> P5 --> P5G
    P5G -- no --> P5
    P5G -- yes --> P6 --> P7 --> P7G
    P7G -- no --> P4
    P7G -- yes --> P8 --> P8G
    P8G -- yes --> P9 --> DONE
    P8G -- no --> DONE

    classDef gate stroke:#d97706,stroke-width:2px;
    class P1G,P5G,P7G,P8G gate
```

Three feedback loops: re-frame when info still missing, re-observe when range stays wide, re-hypothesize when verification fails.

## Observation Methods

Pick by **environment** + **suspect range**:

| Method | Use when | Avoid when |
|---|---|---|
| **chrome-devtools** | Browser: console, network, DOM / CSS, SPA, runtime values | Non-browser scenarios |
| **curl direct probe** | Verify upstream HTTP service; isolate frontend / proxy / SDK layers | Pure compute or stateful pipelines |
| **Add logs** | Backend / CLI / long pipeline; async, concurrent, cross-process | Browser; range already tiny |
| **Read code** | Suspect range is 1-2 files (gate-locked); pure logic; config / typo; small recent diff | Range still wide; runtime-dependent; concurrency |

Decision order:

```text
browser?               -> chrome-devtools
upstream HTTP suspect? -> curl direct probe (mind proxy env)
narrow + pure logic?   -> read code
otherwise              -> add diagnostic logs
```

## Loading Guide

Load only what the current phase needs.

| Reference | Use when |
|---|---|
| `references/frame-problem.md` | Phase 1: bug report missing repro / expected / actual / env |
| `references/scope-triage.md` | Phase 3: deciding suspect layer, ownership, and side |
| `references/debugging-guideline.md` | Phase 4-7: hypotheses, observation, narrowing, fix, verify, cleanup |
| `references/coding-guideline.md` | Before editing code so the fix stays simple, surgical, goal-driven |
| `references/persist-playbook.md` | Phase 9: structure for `docs/debug/<symptom>.md` |

## Boundaries

- This skill covers debugging and root-cause analysis only.
- This skill does not do task orchestration, story breakdown, or agent routing.
- This skill does not justify speculative refactors or unrelated cleanup.
