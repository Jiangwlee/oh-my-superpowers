# Stock Selection Rule Updates

Purpose: Track incremental rule corrections applied to candidate filtering.
Input:   Validated evidence from diagnosis, backtest, or live-trade review.
Output:  Ordered rule updates with effective date and rationale.
Sections: Rule Format | Current Rules | Maintenance Rules

## Rule Format

```markdown
1. <rule statement>
- effective_on: YYYY-MM-DD
- reason: <what failed before>
- expected_effect: <what should improve>
- applies_to: <market regime / stock type>
```

## Current Rules

1. 禁止将“高开且开盘30分钟转弱”的个股列为首笔买入候选
- effective_on: 2026-02-24
- reason: 追高场景在实际交易中导致显著回撤
- expected_effect: 降低首笔建仓失败率和开盘时段回撤
- applies_to: strong/neutral 市场中的短线候选

## Maintenance Rules

1. Add one rule per confirmed behavioral correction.
2. Keep rules executable and measurable; avoid abstract wording.
3. Delete placeholder lines when the first real rule is added.
