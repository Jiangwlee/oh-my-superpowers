# Field Mapping Quick Reference

## Flow IDs
1. `event_id`: produced by market/order event source.
2. `intent_id`: produced by event-executor.
3. `risk_decision_id`: generated when risk decision is persisted.
4. `order_id`: returned by broker adapter.
5. `execution_report_id`: generated when execution report is persisted.

## Object Mapping

### Market Event -> Order Intent
1. `event.symbol` -> `order_intent.symbol`
2. `event.ts` -> `order_intent.ts`
3. `event.trigger` -> `order_intent.reason_code`
4. strategy action -> `order_intent.action`

### Order Intent -> Risk Decision
1. `order_intent.intent_id` -> `risk_decision.intent_id`
2. rule engine outputs -> `risk_decision.rule_results[]`
3. aggregate pass/fail -> `risk_decision.allow`

### Risk Decision -> Execution Report
1. `risk_decision.allow=true` required
2. order request fields -> `execution_report.request`
3. broker response -> `execution_report.response`
4. fills -> `execution_report.fills[]`

### Full Chain -> Event Log
1. `event_id`
2. `intent_id`
3. `risk_decision_id`
4. `execution_report_id`
5. final status

## Derived Trading Fields
1. `last_buy_price`: latest successful buy fill price for symbol.
2. `next_add_price`: `last_buy_price * (1 + 0.02)`.
3. `stop_loss_price`: `last_buy_price * 0.8`.
4. `repost_count_today`: count of `repost_open` for symbol in current day.
5. `fill_count_today`: count of fills across all symbols in current day.

## 5000 Rule + 1 Lot Exception
1. default: `target_amount <= 5000`.
2. exception: if `previous_close * 100 > 5000`, allow order volume `100`.
3. source for `previous_close`: previous trading day close from trusted data source.

## Session Guards
1. allowed sessions: `09:30-11:30` and `13:00-15:00`.
2. opening batch window: `09:30-09:35`.
3. outside sessions: reject with `R_TRADING_SESSION_ONLY`.
