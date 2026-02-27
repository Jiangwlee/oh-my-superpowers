# Trading Plan Execution

Purpose: Produce a next-day trading plan using candidates, execution review, and position constraints.
Input:   Market review, candidates JSON, trade review, holding insight, and optional deep-research briefs.
Output:  `~/.ashare-assistant/data/{DATE}/trading_plan.md`.
Sections: Required Inputs | Pre-Run Scripts | Intraday Tools | Execution Steps | Post-Run Checks | Hard Rules

## Required Inputs

1. `~/.ashare-assistant/data/{DATE}/market_review.md`
2. `~/.ashare-assistant/data/{DATE}/analysis/candidates.json`
3. `~/.ashare-assistant/data/{DATE}/analysis/trade_review.json`
4. `~/.ashare-assistant/data/{DATE}/analysis/holding_insight.json`
5. `~/.ashare-assistant/data/{DATE}/report/dr_*_brief.md` (optional)
6. `skills/ashare-assistant/strategy/active.yaml`
7. `skills/ashare-assistant/evolution/known_pitfalls.md` (optional but recommended)

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
2. Evaluate each executed order quality using intraday tools.
3. Merge market regime and candidates into per-stock action plans.
4. If deep-research briefs exist, apply conviction multiplier; else use `x1.0`.
5. Apply account constraints from `holding_insight.json`.
6. Define per-stock entry condition, take-profit, stop-loss, holding period, and target shares.
7. Round all share counts down to 100-share lots.
8. Ensure total planned exposure aligns with regime guidance.

## Output Template

```markdown
# 交易计划 - {DATE}

## 一、账户状态
## 二、交易复盘（当日执行情况）
## 三、持仓洞察
## 四、明日交易计划
## 五、执行优先级
## 六、仓位分配汇总
## 七、策略回顾
## 八、知识库积累
```

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
