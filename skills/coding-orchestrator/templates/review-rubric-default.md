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

1. Must-Haves: verify every claimed truth, artifact, and key link against the spec.
2. File Scope: flag any edit outside the declared file scope.
3. Deviations: compare the diff against the stated objective and report unapproved scope creep.
4. Tests: confirm the verification layer matches the task's declared intent.

## Output Format

```markdown
## REVIEW COMPLETE

**Task:** task-{task_id}
**Verdict:** PASS | NEEDS_FIX | BLOCKED

### Issues
- [severity] finding — evidence: file:line — suggested fix: one line

### Must-Haves Verified
- <what you confirmed>

### Notes for Orchestrator
- <ambiguities, false positives, or follow-up work>
```

## Additional Instructions

{additional}
