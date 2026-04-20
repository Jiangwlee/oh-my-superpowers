# Review: task-{task_id}

## Story

`{story_name}`

## Spec Path

`{spec_path}`

## Objective

{objective}

## File Scope

{file_scope}

## Acceptance Criteria

{acceptance}

## Changes To Inspect

{changes}

## Review Rubric

Run every check in order and cite `file:line` evidence for each finding.

1. Must-Haves: verify every truth, artifact, and key link from the spec.
2. File Scope: any out-of-scope edit is blocking.
3. Task Decomposition Rules: reject horizontal slicing, orphaned API work, or verification-only churn.
4. Test Layer: confirm the first red test matches the declared acceptance layer.
5. Deviations: reject silent scope expansion or unreported architectural moves.
6. Regression Risk: call out missing cleanup, dead branches, or partial migrations.

## Output Format

```markdown
## REVIEW COMPLETE

**Task:** task-{task_id}
**Verdict:** PASS | NEEDS_FIX | BLOCKED

### Issues
- [severity] finding — evidence: file:line — suggested fix: one line

### Must-Haves Verified
- <what you confirmed>

### Deviations
- <approved or rejected deviations>

### Notes for Orchestrator
- <ambiguities, false positives, or follow-up work>
```

## Additional Instructions

{additional}
