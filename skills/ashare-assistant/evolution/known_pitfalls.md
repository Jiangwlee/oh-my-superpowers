# Known Trading Pitfalls

Purpose: List repeatable trading mistakes that must be checked before plan finalization.
Input:   Confirmed post-trade lessons from diagnosis and execution review.
Output:  Numbered pitfall rules with date and concrete trigger pattern.
Sections: Rule Format | Pitfall List | Maintenance Rules

## Rule Format

```markdown
1. <pitfall title>
- discovered_on: YYYY-MM-DD
- trigger: <observable market/execution pattern>
- consequence: <observed loss or risk>
- prevention: <hard check before order placement>
```

## Pitfall List

1. 高开追涨首笔建仓
- discovered_on: 2026-02-24
- trigger: 开盘后 30 分钟内，个股相对强弱未确认即追价买入
- consequence: 高位接力失败后当日回撤扩大
- prevention: 首笔买入前必须完成 `opening_context` 与 `relative_strength` 双校验

## Maintenance Rules

1. Only keep pitfalls that appeared in real trades.
2. Merge duplicates instead of adding near-identical entries.
3. If a pitfall is retired, mark it as resolved with date and reason.
