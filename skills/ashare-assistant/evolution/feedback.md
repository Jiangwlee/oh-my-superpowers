# Trading Diagnosis Feedback

Purpose: Record dated diagnosis findings that must influence next trading-plan generation.
Input:   Structured diagnosis summary from daily/periodic review.
Output:  Append-only bullet entries grouped by trading date.
Sections: Entry Format | Active Feedback | Update Rules

## Entry Format

For each date, keep one compact block:

```markdown
YYYY-MM-DD 交易复盘
- defects: <error_count> error / <warning_count> warning / <info_count> info
- timing_score: buy <grade>, sell <grade>
- position_compliance: pass|fail
- key_issues: <issue_1>; <issue_2>
- actions: <next-day action_1>; <next-day action_2>
```

## Active Feedback

2026-02-24 交易复盘
- defects: 4 error / 4 warning / 10 info
- timing_score: buy D, sell -
- position_compliance: fail
- key_issues: 严重追高
- actions: 明确禁止高开追涨首笔建仓; 首笔买入前必须核验开盘30分钟强弱

## Update Rules

1. Keep newest entry at the bottom for append-only traceability.
2. Use facts from diagnosis outputs; do not add unverified explanations.
3. Remove stale placeholders once real entries exist.
