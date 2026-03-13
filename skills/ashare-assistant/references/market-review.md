# Market Review Execution

Purpose: Generate the daily market review report with evidence-based regime assessment.
Input:   Daily sentiment, sector, funding, trend, and strategy files under data directory.
Output:  `~/.ashare-assistant/data/{DATE}/market_review.md`.
Sections: Required Inputs | Execution Steps | Output Template | Hard Rules

## Required Inputs

Priority order:

1. Prefer retained platform facts when present:
   - `~/.ashare-assistant/data/{DATE}/report/platform_trend_pool.json`
   - `~/.ashare-assistant/data/{DATE}/report/platform_theme_pool.json`
   - `~/.ashare-assistant/data/{DATE}/report/platform_theme_stocks.json`
   - `~/.ashare-assistant/data/{DATE}/report/platform_market_review.json`
2. `~/.ashare-assistant/data/{DATE}/report/news_sentiment.md`
3. `~/.ashare-assistant/data/{DATE}/report/social_sentiment.md`
4. `~/.ashare-assistant/data/{DATE}/filtered/market_sectors.md`
5. `~/.ashare-assistant/data/{DATE}/filtered/funding.md`
6. `~/.ashare-assistant/data/{DATE}/filtered/ths_report.md`
7. `~/.ashare-assistant/data/{DATE}/filtered/trend_report.md`
8. `~/.ashare-assistant/data/{DATE}/filtered/news_flash.md`
9. `~/.ashare-assistant/data/{DATE}/filtered/us_market.md` (optional)
10. `skills/ashare-assistant/strategy/active.yaml`
11. `skills/ashare-assistant/evolution/feedback.md` (optional but recommended)

Interpretation rule:

- Treat `platform_*.json` as the most reliable retained facts for trend pool,
  theme pool, theme constituents, and prior market-review summary.
- Use legacy `filtered/*.md` files as fallback evidence when platform JSON is
  missing or insufficient.

## Execution Steps

1. Determine market regime: `strong`, `neutral`, or `weak`.
2. Derive position guidance aligned with the regime.
3. Summarize US overnight impact per major index and key tech stocks; if missing, state unavailable reason.
4. Extract themes into three tiers: leading (主线), emerging (新兴), fading (衰退警示).
   If `platform_theme_pool.json` exists, use it as the primary theme source.
5. Provide sentiment evidence with at least:
   - 2 social/community quotes (verbatim, with author handle)
   - 1 news headline
   - State whether capital flow and sentiment are aligned
   - Note any contrarian risks
6. Build candidate analysis for each mentioned stock using the exact format below:

```
### {股票名} ({代码}) 类型：{题材|趋势|题材+趋势}
- 四维标签：趋势[{label}] | 资金[{label}] | 题材[{label}] | 情绪[{label}]
- 共振逻辑：{why thesis + catalyst + capital flow converge}
- 趋势评分：{★ count} {score} | {emoji}{Lx}
- 风险点：{specific risk}
```

   Trend label options: 强趋势 / 稳健趋势 / 趋势走弱 / 趋势已破
   Capital label options: 绝对主力 / 资金活跃 / 无资金关照
   Theme label options: 主线核心 / 主线分支 / 新锐题材 / 无题材热度
   Sentiment label options: 情绪极热 / 情绪温和 / 情绪冷淡
   Emotion level: L1 (coldest) → L5 (hottest); emoji: ⚪L1 🔵L2 🟡L3 🟠L4 🔴L5

7. Include ALL 4-star and 5-star names from `trend_report.md` in the summary table. For each entry state whether it is selected (是/否) and if not, provide the exclusion reason.
   If `platform_trend_pool.json` exists, use it as the primary source of trend
   candidates and only fall back to `trend_report.md` for missing detail.

## Output Template

```markdown
# A股市场复盘报告 - {DATE}

## 一、市场环境
（强弱评级 | 主线风格 | 最终仓位建议 | 判断依据）

## 二、美股前夜影响
（指数基调 | VIX | 逐股联动影响 | 综合预判）

## 三、题材线索
### 主线题材
### 新兴线索
### 衰退警示
### 市场情绪
（整体基调 | 舆情证据 | 资金与情绪一致性 | 反向风险）

## 四、候选股分析
（每股按第6步格式输出）

## 五、风险提示
（集中度风险 | 特殊风险）

## 六、精华言论
（≥5条，含社区原文引用，注明作者）

## 七、趋势候选股汇总
| 股票名称 | 股票代码 | 星数 | 情绪 | 是否入选 | 排除原因（如未入选） |
|---------|---------|------|------|---------|-------------------|
```

## Hard Rules

1. Do not fabricate numbers, events, or quotes.
2. Do not skip "趋势候选股汇总"; it must include every 4-star and 5-star stock from the best available trend source, preferring `platform_trend_pool.json` over `trend_report.md`.
3. Mark uncertain items as `待确认`.
4. Section 四 candidate format is mandatory: 四维标签 + 共振逻辑 + 趋势评分 + 风险点; free-text only is forbidden.
5. Section 六 must have ≥5 verbatim community quotes with author handles.
6. Section 七 table must include a non-empty 排除原因 for every stock marked 否.
