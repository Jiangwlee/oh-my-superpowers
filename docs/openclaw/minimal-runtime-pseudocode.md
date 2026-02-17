# Minimal Runtime Pseudocode

This document maps the OpenClaw trading runtime to concrete pseudocode. It mirrors:
- `docs/openclaw/agent.runtime.yaml`
- `docs/openclaw/schedules.yaml`
- `docs/openclaw/event-routing.yaml`
- `docs/contracts/*.schema.json`

## 1. Main Process

```python
from datetime import datetime


def main():
    cfg = load_yaml("docs/openclaw/agent.runtime.yaml")
    contracts = load_contracts(cfg["contracts"])

    while True:
        now = now_shanghai()

        if is_job_time(now, "preopen_bootstrap"):
            run_preopen_bootstrap(cfg)

        if is_job_time(now, "open_window_execution"):
            run_open_window_loop(cfg, contracts)

        if is_in_market_session(now, cfg["agent"]["market"]["sessions"]):
            run_intraday_event_loop(cfg, contracts)

        if is_job_time(now, "eod_review_and_plan"):
            run_eod_review_and_plan(cfg)

        if is_job_time(now, "postclose_reflection"):
            run_postclose_reflection(cfg)

        sleep(1)
```

## 2. Preopen Bootstrap

```python
def run_preopen_bootstrap(cfg):
    session = {}

    # 1) allocate trade/ws/sql servers
    session["servers"] = allocate_servers_with_retry(
        token=env("JVQ_TOKEN"),
        retry_seconds=cfg["reliability"]["allocate_server_retry"],
    )

    # 2) login broker and get ticket
    session["ticket"] = trade_login(
        server=session["servers"]["trade"],
        token=env("JVQ_TOKEN"),
        account=env("JVQ_BROKER_ACCOUNT"),
        password=env("JVQ_BROKER_PASSWORD"),
    )

    # 3) load today plan
    trade_date = today_str()
    session["plan"] = read_json(f"data/plans/{trade_date}/trade_plan.v1.json")
    validate_json(session["plan"], "docs/contracts/trade_plan.schema.json")

    write_json("data/runtime/session.json", session)
```

## 3. Event-Driven Pipeline

```python
def process_event(event, cfg, contracts, state):
    # stage 1: event-executor
    intent = skill_event_executor(
        event=event,
        plan=state.plan,
        positions=state.positions,
        orders=state.orders,
        params=state.params,
    )
    validate_json(intent, contracts["order_intent"])

    # stage 2: risk-gate
    decision = skill_risk_gate(
        intent=intent,
        fill_count=state.fill_count,
        positions=state.positions,
        ladder_state=state.ladder_state,
    )
    validate_json(decision, contracts["risk_decision"])

    if not decision["allow"]:
        append_event_log(event, intent, decision, execution_report=None, status="rejected")
        push_user("risk_reject", {"event": event, "intent": intent, "decision": decision})
        return

    # stage 3: broker-adapter
    report = skill_broker_adapter_jvquant(
        intent=intent,
        decision=decision,
        servers=state.session["servers"],
        ticket=state.session["ticket"],
    )
    validate_json(report, contracts["execution_report"])

    # stage 4: ledger
    append_event_log(event, intent, decision, report, status=derive_status(report))
    update_positions_and_counters(state, report)
    push_user("trade_complete", {"intent": intent, "report": report})
```

## 4. Required Risk Rules

```python
def check_rules(intent, state):
    results = []

    results.append(rule("R_DAILY_FILL_LE_10", state.fill_count < 10))
    results.append(rule("R_POSITIONS_LE_5", state.concurrent_symbols <= 5))

    if intent["action"] == "add":
        results.append(rule(
            "R_ADD_REQUIRES_LAST_BUY_PLUS_2PCT",
            state.last_price(intent["symbol"]) >= state.next_add_price(intent["symbol"]),
        ))

    results.append(rule(
        "R_STOP_LOSS_FROM_LAST_BUY_80PCT",
        state.stop_loss_price(intent["symbol"]) == state.last_buy_price(intent["symbol"]) * 0.8,
    ))

    results.append(rule(
        "R_SINGLE_ORDER_LE_5000_OR_1LOT_EXCEPTION_PREVCLOSE",
        check_single_order_limit_with_prev_close_exception(intent, state),
    ))

    if intent["action"] == "repost_open":
        results.append(rule("R_REPOST_COUNT_LE_5", state.repost_count(intent["symbol"]) < 5))

    results.append(rule("R_TRADING_SESSION_ONLY", in_market_time(now_shanghai())))

    allow = all(x["pass"] for x in results)
    return {"allow": allow, "rule_results": results}
```

## 5. Open Window Logic (09:30-09:35)

```python
def run_open_window_loop(cfg, contracts):
    state = load_runtime_state()
    while in_open_window(cfg["trading_rules"]["open_window"]):
        event = next_market_or_order_event(timeout=1)
        if not event:
            continue
        process_event(event, cfg, contracts, state)
```

## 6. Intraday Event Loop

```python
def run_intraday_event_loop(cfg, contracts):
    state = load_runtime_state()

    # websocket as primary source
    event = next_market_or_order_event(timeout=1)
    if event:
        process_event(event, cfg, contracts, state)
        return

    # optional fallback check when websocket unstable
    if websocket_unstable_for_too_long():
        state.positions = query_hold_snapshot()
        raise_alert("ws_unstable_fallback_mode")
```

## 7. End-of-Day

```python
def run_eod_review_and_plan(cfg):
    run_skill("a-share-trend-scanner")
    run_skill("a-share-trade-plan-compiler")


def run_postclose_reflection(cfg):
    run_skill("a-share-trade-reflection-evolver")
```

## 8. Integration Checklist

1. Add runtime storage directories:
   - `data/runtime`
   - `data/events`
   - `data/orders`
   - `data/positions`
2. Implement wrappers for 6 trading skills.
3. Plug jvquant HTTP/WS client into broker adapter wrapper.
4. Implement `append_event_log` as append-only JSONL.
5. Implement user push integration for:
   - `trade_complete`
   - `risk_reject`
   - `uncertain_order_state`

