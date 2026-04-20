# Task Skeleton Reviewer Prompt

Use this prompt when the orchestrator finishes the initial task skeleton in Phase 1.
Dispatch it to an L3 reasoning-capable reviewer before wave 1 begins.

## Input

- The story design doc
- The proposed `tasks.yaml` skeleton
- Any wave-1 task specs already drafted

## Checklist

1. Adjacent tasks with no real code dependency should be merged.
2. If the same file is touched across multiple nearby tasks, prefer merging into one vertical slice.
3. Any task smaller than one realistic RED-GREEN cycle should be merged.
4. If independent tasks were placed in later waves without dependency, propose `rewave`.
5. If E2E/docs were split only as action-sequence chores, merge them back into implementation work.

## Output

Return JSON only:

```json
{
  "merge": [["02", "03"]],
  "split": [],
  "rewave": [["04", 2]]
}
```
