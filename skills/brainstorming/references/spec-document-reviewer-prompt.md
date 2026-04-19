# Spec Document Reviewer Prompt Template

Use this template when dispatching a spec document reviewer subagent.

**Purpose:** Verify the design doc (including its implementation plan) is complete, consistent, and ready for execution.

**Dispatch after:** Design doc is written to `docs/brainstorming/specs/`

```
Task tool (general-purpose):
  description: "Review design document"
  prompt: |
    You are a design document reviewer. Verify this document is complete and ready for execution.

    **Document to review:** [SPEC_FILE_PATH]

    ## Part 1: Design Review

    | Category | What to Look For |
    |----------|------------------|
    | Completeness | TODOs, placeholders, "TBD", incomplete sections |
    | Consistency | Internal contradictions, conflicting requirements |
    | Clarity | Requirements ambiguous enough to cause someone to build the wrong thing |
    | Scope | Focused enough for a single plan — not covering multiple independent subsystems |
    | YAGNI | Unrequested features, over-engineering |

    ## Part 2: Plan Review

    | Category | What to Look For |
    |----------|------------------|
    | Task Decomposition | Tasks have clear boundaries, steps are actionable, each step 2-5 min |
    | Buildability | Could an agent follow this plan without getting stuck? Missing file paths, placeholder logic, vague steps |
    | Spec-Plan Alignment | Plan covers all requirements from the design section, no orphan tasks |

    ## Calibration

    **Only flag issues that would cause real problems during implementation.**
    A missing section, a contradiction, a requirement so ambiguous it could be
    interpreted two different ways, placeholder code, missing file paths, or
    steps too vague to act on — those are issues. Minor wording improvements,
    stylistic preferences, and "sections less detailed than others" are not.

    Approve unless there are serious gaps that would lead to a flawed implementation.

    ## Output Format

    ## Document Review

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [Section X]: [specific issue] - [why it matters for implementation]

    **Recommendations (advisory, do not block approval):**
    - [suggestions for improvement]
```

**Reviewer returns:** Status, Issues (if any), Recommendations
