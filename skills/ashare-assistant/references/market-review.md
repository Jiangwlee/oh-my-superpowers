# Market Review Execution

Purpose: Generate the daily market review report with evidence-based regime assessment.
Input:   Daily sentiment, sector, funding, trend, and strategy files under data directory.
Output:  `~/.ashare-assistant/data/{DATE}/market_review.md`.
Sections: Required Inputs | Execution Steps | Output Template | Hard Rules

## Required Inputs

1. `~/.ashare-assistant/data/{DATE}/report/news_sentiment.md`
2. `~/.ashare-assistant/data/{DATE}/report/social_sentiment.md`
3. `~/.ashare-assistant/data/{DATE}/filtered/market_sectors.md`
4. `~/.ashare-assistant/data/{DATE}/filtered/funding.md`
5. `~/.ashare-assistant/data/{DATE}/filtered/ths_report.md`
6. `~/.ashare-assistant/data/{DATE}/filtered/trend_report.md`
7. `~/.ashare-assistant/data/{DATE}/filtered/news_flash.md`
8. `~/.ashare-assistant/data/{DATE}/filtered/us_market.md` (optional)
9. `skills/ashare-assistant/strategy/active.yaml`
10. `skills/ashare-assistant/evolution/feedback.md` (optional but recommended)

## Execution Steps

1. Determine market regime: `strong`, `neutral`, or `weak`.
2. Derive position guidance aligned with the regime.
3. Summarize US overnight impact; if missing, state unavailable reason.
4. Extract themes: leading, emerging, and fading sectors.
5. Provide sentiment evidence with at least:
   - 2 social/community观点
   - 1 news headline
6. Build candidate analysis for each mentioned stock:
   - thesis
   - risk
7. Include all 4-star and 5-star names from `trend_report.md` in a dedicated summary section.

## Output Template

```markdown
# A股市场复盘报告 - {DATE}

## 一、市场环境
## 二、美股前夜影响
## 三、题材线索
## 四、候选股分析
## 五、风险提示
## 六、精华言论
## 七、趋势候选股汇总
```

## Hard Rules

1. Do not fabricate numbers, events, or quotes.
2. Do not skip "趋势候选股汇总".
3. Mark uncertain items as `待确认`.
