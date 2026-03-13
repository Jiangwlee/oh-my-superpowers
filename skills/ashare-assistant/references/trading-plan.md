# Trading Plan Execution

Purpose: Produce a next-day trading plan using candidates, execution review, position constraints, and watchlist signals.
Input:   Market review, candidates JSON, trade review, holding insight, watchlist signals, and optional deep-research briefs.
Output:  `~/.ashare-assistant/data/{DATE}/trading_plan.md`.
Sections: Required Inputs | Pre-Run Scripts | Intraday Tools | Execution Steps | Section Specs | Post-Run Checks | Hard Rules

## Required Inputs

1. `~/.ashare-assistant/data/{DATE}/market_review.md`
2. `~/.ashare-assistant/data/{DATE}/analysis/candidates.json`
3. `~/.ashare-assistant/data/{DATE}/analysis/trade_review.json`
4. `~/.ashare-assistant/data/{DATE}/analysis/holding_insight.json`
5. `~/.ashare-assistant/signals/watchlist_signals.json` (optional, read if present)
6. `~/.ashare-assistant/data/{DATE}/report/dr_*_brief.md` (optional)
7. `skills/ashare-assistant/strategy/active.yaml`
8. `skills/ashare-assistant/evolution/known_pitfalls.md` (optional but recommended)
9. Optional retained platform facts:
   - `~/.ashare-assistant/data/{DATE}/report/platform_trend_pool.json`
   - `~/.ashare-assistant/data/{DATE}/report/platform_theme_pool.json`
   - `~/.ashare-assistant/data/{DATE}/report/platform_market_review.json`

Interpretation rule:

- If retained platform facts exist, prefer them when discussing theme strength,
  trend quality, and prior market context.
- Legacy files remain valid fallback sources.

## Pre-Run Scripts

```bash
DATE=$(date +%Y-%m-%d)

python3 -m scripts.trade_review \
  --output ~/.ashare-assistant/data/${DATE}/analysis/trade_review.json \
  --strategy strategy/active.yaml

python3 -m scripts.holding_insight \
  --output ~/.ashare-assistant/data/${DATE}/analysis/holding_insight.json \
  --strategy strategy/active.yaml
```

## Intraday Tools

```bash
python3 -m scripts.intraday_summary --code {CODE} --date {YYYYMMDD}
python3 -m scripts.trade_context --code {CODE} --date {YYYYMMDD} --time {HHMMSS} --price {PRICE} --window 30
python3 -m scripts.opening_context --code {CODE} --date {YYYYMMDD}
python3 -m scripts.relative_strength --code {CODE} --date {YYYYMMDD} --benchmark 000001
```

## Execution Steps

1. Read `trade_review.json` for account facts and compliance context.
2. If `watchlist_signals.json` exists, cross-reference it against today's buy orders in `trade_review.json` order_list.
3. Compute account health metrics (cash ratio, position count, violation count) and output red/yellow/green ratings.
4. Evaluate each executed order using intraday tools; infer root cause for each violation (choose from the five defined categories).
5. Merge market regime and `candidates.json` to derive per-position disposition priority (immediate / today / hold).
   When platform retained facts exist, use them to verify whether the
   candidates still align with the strongest themes and trend pool.
6. Convert `holding_insight.json` decisions into per-position if-then tables (take-profit / hold / stop-loss, one row each).
7. If deep-research briefs exist, apply conviction multiplier; else use `x1.0`.
8. Round all share counts down to 100-share lots.
9. Ensure total planned exposure aligns with regime guidance.

## Output Template

```markdown
# 交易计划 - {DATE}

## 零、信号对照
## 一、账户快照 + 健康指标
## 二、交易复盘 + 根因分析
## 三、持仓健康检查
## 四、明日持仓计划
## 五、明日候补机会
## 六、执行优先级
## 七、策略回顾
## 八、知识库积累
```

## Section Specs

### Section 0: Signal Comparison

If `watchlist_signals.json` exists, cross-reference it against today's buys (side=buy records in `trade_review.json` order_list):

```
Signal match rate = buys that appear in signal list / total buys today

Notes:
- `watchlist_signals.json` now uses state-machine fields.
- Valid state values: `SETUP`, `ENTRY`, `HOLD`, `REDUCE`, `EXIT`.
- For buy-order alignment, treat only `ENTRY` as direct signal match.

| Stock | Bought today | In signal list | Signal state | Assessment |
|-------|-------------|---------------|--------------|------------|
| StockA | ✓ | ✗ | — | Unplanned (impulsive?) |
| StockB | ✓ | ✓ | ENTRY | Matches signal |
```

Interpretation rules:
- Match rate < 50% → today's trades were driven by intraday emotions; **must** flag this in Section 2 problem diagnosis
- Match rate ≥ 80% → execution aligned with plan
- If `watchlist_signals.json` does not exist, output "No signal file found, skipping."

---

### Section 1: Account Snapshot + Health Metrics

Output the account overview table (cash, total assets, position count, etc.), then a mandatory health metrics table:

```
| Metric | Value | Rating |
|--------|-------|--------|
| Cash ratio | X% | 🔴/🟡/🟢 |
| Position count | N | 🔴/🟡/🟢 |
| Concentration (top-3 share) | X% | 🔴/🟡/🟢 |
| Rule violations today | N | 🔴/🟡/🟢 |
```

Rating thresholds:
- Cash ratio: < 10% 🔴, 10%-20% 🟡, > 20% 🟢
- Position count: > 5 🔴, 3-5 🟡, ≤ 3 🟢
- Violations: > 2 🔴, 1-2 🟡, 0 🟢

Data sources: `trade_review.json` (flaws, account_snapshot) + `holding_insight.json` (summary)

---

### Section 2: Trade Review + Root Cause Analysis

First list today's execution facts (each fill: stock, side, price, shares, P&L). Then for each violation output a **two-layer diagnosis**:

```
### 🔴 Issue N: [symptom title]
- Fact: [quantifiable, specific fact]
- Root cause: [choose one from the list below]
- Consequence: [impact on the account]
```

Root cause categories (LLM must choose exactly one; no new categories allowed):
- No pre-market plan
- Plan existed but not followed (discipline failure)
- FOMO / emotional impulse
- Technical misjudgment (MA level or trend direction wrong)
- Data unavailable (no volume data or historical K-line)

If no violations exist, output "No violations recorded today."

---

### Section 3: Position Health Check

```
### Overall rating: 🔴/🟡/🟢
Reason: [1-2 sentences]

### Disposition priority
1. 🔴 Must exit today: [stock list]  (urgency=immediate)
2. 🟡 Exit if conditions met: [stock list]  (urgency=today)
3. 🟢 Can hold: [stock list]  (urgency=watch or bought low with intact trend)

### Available capital estimate for tomorrow
- Current cash X + expected proceeds from sells Y = available Z
- New entries: max N positions (per strategy position-limit rule)
```

Data sources: `holding_insight.json` (decisions.urgency), `trade_review.json` (flaws)

---

### Section 4: Tomorrow's Position Plan

Output an if-then scenario table for every open position. Vague language is forbidden.

```
#### {Stock name} ({code})  {shares} shares | Cost {price} | Current P&L {P&L}

| Scenario | Trigger condition | Action |
|----------|------------------|--------|
| Take profit | [specific price or technical condition] | Sell all at market / reduce N% |
| Hold | [specific price range] | Do nothing |
| Stop loss | [specific price, unconditional] | Sell all at market |
```

Hard rules for Section 4:
- Every position **must have exactly 3 rows** (take-profit / hold / stop-loss); none may be omitted.
- Stop-loss price is mandatory and must align with `stop_loss` in `holding_insight.json` decisions.
- **Forbidden phrases**: "sell on spike", "wait for rebound", "depends on situation", "observe", or any emotional description.
- Trigger conditions must be a price number or an objectively verifiable technical indicator.

## Post-Run Checks

```bash
DATE=$(date +%Y-%m-%d)

python3 -m scripts.risk_check \
  --input ~/.ashare-assistant/data/${DATE}/analysis/candidates.json

python3 -m scripts.decision_logger \
  --input ~/.ashare-assistant/data/${DATE}/analysis/candidates.json
```

## Hard Rules

1. Do not introduce stocks or prices not present in inputs.
2. Share counts must be multiples of 100.
3. If `risk_check` fails, revise and rerun until pass.
4. Treat `position_flaw` and `discipline_flaw` as hard constraints.
5. Section 4: every position must output exactly 3 rows (take-profit / hold / stop-loss); vague trigger conditions are forbidden.
6. Section 2: every violation must include a root cause chosen from the five defined categories.
7. If signal match rate < 50%, Section 2 problem diagnosis must explicitly mention unplanned buys.
