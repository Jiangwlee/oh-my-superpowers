---
name: ashare-assistant
description: >-
  Run the A-share daily workflow for market review, stock picking, and trading planning.
  Use when user asks for "复盘", "选股", "交易计划", "明天买什么", or "review".
metadata:
  author: mindora
  version: 0.2.0
---

# A-Share Assistant

Purpose: Generate a daily A-share market review, candidate list, and trading plan.
Input:   `~/.ashare-assistant/data/{DATE}/filtered/` data and strategy config.
Output:  `market_review.md`, `analysis/candidates.json`, `trading_plan.md`.
Sections: Prerequisite Check | Workflow | Failure Handling | Done Criteria | Guardrails

## Prerequisite Check

Run all commands from the skill install directory. Scripts use relative imports
and must be invoked with `-m scripts.<module>`; running them directly as
`python3 scripts/foo.py` will raise `ModuleNotFoundError`.

```bash
# Correct — run from skill install directory
cd <skill_install_dir>
python3 -m scripts.trade_review --output ...

# Wrong — will fail with ModuleNotFoundError
python3 scripts/trade_review.py --output ...
```

If `python3` is unavailable, try `python` instead (or vice versa).

```bash
DATE=$(date +%Y-%m-%d)
DATA_DIR="$HOME/.ashare-assistant/data/${DATE}"

if [ ! -d "${DATA_DIR}/filtered" ] || [ -z "$(ls -A "${DATA_DIR}/filtered" 2>/dev/null)" ]; then
  ashare-collect --date "${DATE}" --verbose
fi
```

Required files before Step 2:

1. `${DATA_DIR}/filtered/index.md`
2. `strategy/active.yaml`

## Workflow

1. Generate market review.
Read and follow `references/market-review.md`.
Output must be `${DATA_DIR}/market_review.md`.

2. Generate stock candidates.
Read and follow `references/stock-pick.md`.
Output must be `${DATA_DIR}/analysis/candidates.json`.

3. Generate trading plan.
Read and follow `references/trading-plan.md`.
Output must be `${DATA_DIR}/trading_plan.md`.

4. Run risk checks and decision logging.

```bash
python3 -m scripts.risk_check --input "${DATA_DIR}/analysis/candidates.json"
python3 -m scripts.validate_output --input "${DATA_DIR}/analysis/candidates.json" || true
python3 -m scripts.decision_logger --input "${DATA_DIR}/analysis/candidates.json"
```

## Failure Handling

1. If data collection fails, stop and report missing source files.
2. If `risk_check` fails, revise `trading_plan.md` and rerun checks.
3. If logging fails, do not mark workflow complete.

## Done Criteria

All items must pass:

1. `${DATA_DIR}/market_review.md` exists and is non-empty.
2. `${DATA_DIR}/analysis/candidates.json` exists and is valid JSON.
3. `${DATA_DIR}/trading_plan.md` exists and is non-empty.
4. `risk_check` exits with code 0.
5. `decision_logger` exits with code 0.

## Guardrails

<HARD-GATE>
1. NO step N+1 WITHOUT finishing step N.
2. NO fabrication. Use only facts present in input files.
3. Follow A-share constraints: T+1, 100-share lot size, limit-up/limit-down rules.
4. If risk checks fail, revise outputs and rerun; do not end early.
</HARD-GATE>

## References

1. `references/market-review.md`
2. `references/stock-pick.md`
3. `references/trading-plan.md`
4. `evolution/feedback.md`
5. `evolution/known_pitfalls.md`
6. `evolution/selection_rules.md`
