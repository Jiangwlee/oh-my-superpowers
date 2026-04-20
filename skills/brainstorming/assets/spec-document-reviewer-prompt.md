# Spec Document Reviewer Prompt

Review the generated spec document as a design reviewer, not as an implementer.

## What to check

1. Is the problem statement concrete and scoped?
2. Are the proposed sections internally consistent?
3. Are risks and assumptions explicit?
4. Is there unnecessary complexity or speculative abstraction?
5. Does the action plan map cleanly to the design?

## Output format

```markdown
## SPEC REVIEW

### Blocking
- <issue or "none">

### Advisory
- <issue or "none">

### Verdict
- PASS | REVISE
```
