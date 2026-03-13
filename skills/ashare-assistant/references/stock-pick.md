# Stock Pick Execution

Purpose: Convert market review conclusions into a schema-valid candidate list.
Input:   `market_review.md` and `filtered/run_id.md` for the same trading date.
Output:  `~/.ashare-assistant/data/{DATE}/analysis/candidates.json`.
Sections: Required Inputs | Mapping Rules | Output Schema | Validation | Hard Rules

## Required Inputs

1. `~/.ashare-assistant/data/{DATE}/market_review.md`
2. Prefer `~/.ashare-assistant/data/{DATE}/report/platform_trend_pool.json` and
   `~/.ashare-assistant/data/{DATE}/report/platform_theme_pool.json` when present
3. `~/.ashare-assistant/data/{DATE}/filtered/run_id.md`
3. `skills/ashare-assistant/evolution/selection_rules.md` (optional but recommended)

## Mapping Rules

1. Extract `market.regime` from the market review.
2. Build candidate rows with fields:
   - `code`, `name`, `sector`, `thesis_short`, `risk_note`, `trigger_condition`
   Prefer stocks that are confirmed by retained platform facts:
   - trend candidates from `platform_trend_pool.json`
   - main themes from `platform_theme_pool.json`
3. Normalize action values:
   - 买入/建仓 -> `buy`
   - 持有 -> `hold`
   - 卖出/清仓 -> `sell`
   - 其他 -> `watch`
4. Keep `position` as `0` for all candidates.
5. Keep `thesis_short` and `risk_note` within 30 Chinese characters each.
6. `trigger_condition` is required (≤40 chars). Describe what condition must be met to execute the action:
   - `buy`: entry trigger (e.g. "pull back to MA10 with shrinking volume")
   - `sell`: exit trigger (e.g. "break below yesterday's low or surge to resistance")
   - `watch`: condition to upgrade to buy (e.g. "breakout above prior high on volume")
   - `hold`: condition to keep holding (e.g. "MA5 support holds")

## Output Schema

```json
{
  "run_id": "YYYYMMDD-xxx-HHMMSS",
  "as_of_date": "YYYY-MM-DD",
  "market": { "regime": "strong" },
  "candidates": [
    {
      "code": "000001",
      "name": "示例",
      "score": 4.0,
      "type": "trend",
      "action": "watch",
      "sector": "示例板块",
      "position": 0,
      "thesis_short": "30字以内",
      "risk_note": "30字以内",
      "trigger_condition": "放量突破前高且大盘不破3200"
    }
  ],
  "risk_flags": {
    "data_degraded": false,
    "output_schema_invalid": false,
    "strategy_version_fallback": false
  }
}
```

## Validation

```bash
python3 -m scripts.validate_output \
  --input ~/.ashare-assistant/data/{DATE}/analysis/candidates.json || true
```

## Hard Rules

1. Do not add or remove top-level schema fields.
2. `action` must be one of `buy/hold/sell/watch`.
3. `position` must stay `0`.
4. All facts must be traceable to input files.
5. `trigger_condition` must not be empty or vague (e.g. "depends on situation" is forbidden).
