#!/usr/bin/env python3
"""Post-close decision pipeline for watchlist stocks.

Purpose: Build next-day trading decisions from watchlist + JRJ daily/weekly bars.
Input:   ~/.ashare-assistant/memory/watchlist.json and optional broker holdings.
Output:  ~/.ashare-assistant/signals/post_close_decisions.json plus persisted state.

Public API:
    run_pipeline() -> dict[str, Any]  -- compute and write post-close decisions
    main() -> None                    -- CLI entry point
"""

from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ashare_data.core.config import ASHARE_HOME
from ashare_data.core.governance import load_latest_run_id
from ashare_data.core.utils import atomic_write_json
from ashare_data.core.watchlist import load as load_watchlist
from ashare_data.core.http_client import http_json
from ashare_data.core.utils import norm_price
from ashare_data.fetchers.broker_account import fetch_broker_account

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))
_SIGNALS_DIR = ASHARE_HOME / "signals"
_OUTPUT_FILE = _SIGNALS_DIR / "post_close_decisions.json"
_STATE_FILE = ASHARE_HOME / "memory" / "post_close_state.json"
_OUTPUT_SCHEMA_VERSION = "1.0"

_DEFAULT_PARAMS: dict[str, float | int] = {
    "stage1_threshold": 0.18,
    "stage2_threshold": 0.22,
    "pullback_band": 0.03,
    "stop_buffer": 0.015,
    "reduce_ma5d_dev": 0.10,
    "reduce_pct": 0.30,
    "reduce_cooldown_days": 5,
    "open_size_stage1": 0.25,
    "open_size_stage2": 0.10,
    "max_position": 0.50,
    "new_high_weeks": 8,
}


@dataclass
class _KlineBar:
    """Normalized kline bar."""

    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float


def _to_jrj_security_id(code: str) -> str:
    return f"1{code}" if code.startswith("6") else f"2{code}"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _determine_stage(dev20w: float, previous_stage: str | None) -> str:
    """Determine stage with hysteresis band to avoid thrashing around 20%."""
    if dev20w <= float(_DEFAULT_PARAMS["stage1_threshold"]):
        return "stage1"
    if dev20w >= float(_DEFAULT_PARAMS["stage2_threshold"]):
        return "stage2"
    if previous_stage in {"stage1", "stage2"}:
        return previous_stage
    return "stage2" if dev20w > 0.20 else "stage1"


def _resolve_entry_stage(
    *, code: str, current_stage: str, hold_vol: int, state: dict[str, dict[str, Any]]
) -> str:
    """Lock existing positions to original stage to keep risk model stable."""
    old = state.get(code, {})
    if hold_vol > 0 and isinstance(old.get("entry_stage"), str):
        return str(old["entry_stage"])
    return current_stage


def _decide_holding_action(
    *,
    close_w: float,
    ma10w: float,
    ma5d_dev: float,
    entry_stage: str,
    reduce_allowed: bool,
    stop_buffer: float,
) -> str:
    """Apply fixed priority: exit > reduce > add/open (handled outside)."""
    if ma10w > 0 and close_w < ma10w * (1.0 - stop_buffer):
        return "exit"
    if reduce_allowed and ma5d_dev >= float(_DEFAULT_PARAMS["reduce_ma5d_dev"]):
        return "reduce"
    return "hold"


def _capped_target_position(existing: float, add_size: float, cap: float) -> float:
    return round(min(existing + add_size, cap), 4)


def _load_state() -> dict[str, dict[str, Any]]:
    if not _STATE_FILE.exists():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        logger.exception("读取 post_close_state.json 失败")
    return {}


def _save_state(state: dict[str, dict[str, Any]]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(_STATE_FILE, state)


def _can_reduce_today(
    code: str,
    state: dict[str, dict[str, Any]],
    today: date,
    cooldown_days: int,
) -> bool:
    raw = state.get(code, {}).get("last_reduce_at")
    if not isinstance(raw, str):
        return True
    try:
        last = date.fromisoformat(raw)
    except ValueError:
        return True
    return (today - last).days >= cooldown_days


def _mark_reduce(code: str, state: dict[str, dict[str, Any]], today: date) -> None:
    entry = state.setdefault(code, {})
    entry["last_reduce_at"] = today.isoformat()


def _parse_jrj_bars(items: list[dict[str, Any]]) -> list[_KlineBar]:
    bars: list[_KlineBar] = []
    for item in items:
        t = item.get("nTime") or item.get("time")
        if not t:
            continue
        ts = str(int(t))
        if len(ts) != 8:
            continue
        try:
            bar = _KlineBar(
                date=f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
                open=norm_price(item.get("nOpenPx") or item.get("open") or 0.0),
                close=norm_price(item.get("nLastPx") or item.get("close") or 0.0),
                high=norm_price(item.get("nHighPx") or item.get("high") or 0.0),
                low=norm_price(item.get("nLowPx") or item.get("low") or 0.0),
                volume=float(item.get("llVolume") or item.get("volume") or 0.0) / 100.0,
            )
        except (TypeError, ValueError):
            continue
        if min(bar.open, bar.close, bar.high, bar.low) <= 0:
            continue
        bars.append(bar)
    bars.sort(key=lambda b: b.date)
    return bars


def _fetch_jrj_kline(code: str, ktype: str, count: int) -> list[_KlineBar]:
    secid = _to_jrj_security_id(code)
    url = "https://gateway.jrj.com/quot-kline?" + urlencode(
        {
            "format": "json",
            "securityId": secid,
            "type": ktype,
            "direction": "left",
            "range.num": str(count),
        }
    )
    try:
        data = http_json(url, timeout=12, retries=2)
    except Exception:
        logger.exception("JRJ %s K线拉取失败: %s", ktype, code)
        return []

    if isinstance(data, dict) and isinstance(data.get("value"), str):
        try:
            data = json.loads(data["value"])
        except json.JSONDecodeError:
            pass

    payload: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), dict):
            payload = data["data"].get("kline", []) or []
        elif isinstance(data.get("kline"), list):
            payload = data["kline"]
    return _parse_jrj_bars(payload)


def _load_watchlist_active() -> list[dict[str, Any]]:
    items = load_watchlist()
    return [s for s in items if s.get("status") == "active" and str(s.get("code", "")).strip()]


def _load_holdings() -> dict[str, dict[str, Any]]:
    try:
        data = fetch_broker_account()
    except Exception as exc:
        logger.warning("持仓数据不可用，按空持仓处理: %s", exc)
        return {}
    hold_list = data.get("hold_list", [])
    out: dict[str, dict[str, Any]] = {}
    for item in hold_list:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).strip()
        if not code:
            continue
        try:
            hold_vol = int(item.get("hold_vol", 0) or 0)
        except (TypeError, ValueError):
            hold_vol = 0
        if hold_vol <= 0:
            continue
        out[code] = item
    return out


def _extract_existing_position(holding: dict[str, Any]) -> float:
    raw = holding.get("position")
    if raw is None:
        return 0.0
    try:
        pct = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if pct > 1.0:
        pct = pct / 100.0
    return max(0.0, min(1.0, pct))


def _is_bullish_daily(daily: list[_KlineBar]) -> bool:
    if not daily:
        return False
    return daily[-1].close > daily[-1].open


def _weekly_new_high(weekly: list[_KlineBar], lookback: int) -> bool:
    if len(weekly) < lookback + 1:
        return False
    close_w = weekly[-1].close
    prev_high = max(b.close for b in weekly[-(lookback + 1):-1])
    return close_w > prev_high


def _build_decision(
    *,
    stock: dict[str, Any],
    daily: list[_KlineBar],
    weekly: list[_KlineBar],
    holdings: dict[str, dict[str, Any]],
    state: dict[str, dict[str, Any]],
    today: date,
    params: dict[str, float | int],
) -> dict[str, Any] | None:
    code = str(stock.get("code", "")).strip()
    if not code or len(daily) < 25 or len(weekly) < 20:
        return None

    close_d = daily[-1].close
    close_w = weekly[-1].close
    ma5d = _mean([b.close for b in daily[-5:]])
    ma10d = _mean([b.close for b in daily[-10:]])
    ma20d = _mean([b.close for b in daily[-20:]])
    ma5w = _mean([b.close for b in weekly[-5:]])
    ma10w = _mean([b.close for b in weekly[-10:]])
    ma20w = _mean([b.close for b in weekly[-20:]])
    avg_vol20 = _mean([b.volume for b in daily[-20:]])

    if min(ma5d, ma10d, ma20d, ma5w, ma10w, ma20w) <= 0:
        return None

    dev20w = (close_w - ma20w) / ma20w
    ma5d_dev = (close_d - ma5d) / ma5d
    pullback_ok = abs((close_d - ma5w) / ma5w) <= float(params["pullback_band"])
    vr20d = daily[-1].volume / avg_vol20 if avg_vol20 > 0 else 0.0

    old_state = state.get(code, {})
    current_stage = _determine_stage(dev20w, old_state.get("last_stage"))

    holding = holdings.get(code, {})
    hold_vol = int(holding.get("hold_vol", 0) or 0) if holding else 0
    existing_pos = _extract_existing_position(holding)

    entry_stage = _resolve_entry_stage(
        code=code,
        current_stage=current_stage,
        hold_vol=hold_vol,
        state=state,
    )

    reduce_allowed = _can_reduce_today(
        code,
        state,
        today,
        cooldown_days=int(params["reduce_cooldown_days"]),
    )
    action = _decide_holding_action(
        close_w=close_w,
        ma10w=ma10w,
        ma5d_dev=ma5d_dev,
        entry_stage=entry_stage,
        reduce_allowed=reduce_allowed,
        stop_buffer=float(params["stop_buffer"]),
    )

    target_pos = existing_pos
    reason = ""
    add_size = 0.0

    # Priority 1-2 handled already: exit/reduce.
    if action == "exit":
        target_pos = 0.0
        reason = "周线收盘有效跌破MA10W，执行清仓"
    elif action == "reduce":
        target_pos = max(0.0, existing_pos - float(params["reduce_pct"]))
        _mark_reduce(code, state, today)
        reason = "偏离MA5D超过10%，执行减仓30%"
    else:
        bullish = _is_bullish_daily(daily)
        is_stage2_confirmed = current_stage == "stage2" and _weekly_new_high(
            weekly,
            lookback=int(params["new_high_weeks"]),
        )
        can_open = hold_vol == 0 and pullback_ok and bullish
        can_add = hold_vol > 0 and pullback_ok and bullish

        if can_open:
            if current_stage == "stage1":
                add_size = float(params["open_size_stage1"])
            elif is_stage2_confirmed:
                add_size = float(params["open_size_stage2"])
            if add_size > 0:
                action = "open"
                target_pos = _capped_target_position(
                    existing_pos,
                    add_size,
                    float(params["max_position"]),
                )
                reason = "回踩MA5W且收阳，触发开仓信号"
        elif can_add:
            if entry_stage == "stage1":
                add_size = float(params["open_size_stage1"])
            elif current_stage == "stage2" and is_stage2_confirmed:
                add_size = float(params["open_size_stage2"])
            if add_size > 0:
                action = "add"
                target_pos = _capped_target_position(
                    existing_pos,
                    add_size,
                    float(params["max_position"]),
                )
                reason = "回踩MA5W且收阳，触发加仓信号"

    if not reason:
        reason = "未触发更高优先级交易动作，维持持仓"

    state_entry = state.setdefault(code, {})
    state_entry["last_stage"] = current_stage
    if hold_vol > 0 or action in {"open", "add"}:
        state_entry["entry_stage"] = entry_stage if hold_vol > 0 else current_stage

    decision = {
        "code": code,
        "name": stock.get("name", code),
        "action": action,
        "reason": reason,
        "stage": current_stage,
        "entry_stage": state_entry.get("entry_stage"),
        "position": {
            "current": round(existing_pos, 4),
            "target": round(target_pos, 4),
            "add_size": round(add_size, 4),
            "max_cap": float(params["max_position"]),
        },
        "risk": {
            "stop_basis": "ma10w",
            "stop_price": round(ma10w * (1.0 - float(params["stop_buffer"])), 3),
            "reduce_cooldown_days": int(params["reduce_cooldown_days"]),
        },
        "indicators": {
            "close_d": round(close_d, 3),
            "close_w": round(close_w, 3),
            "ma5d": round(ma5d, 3),
            "ma10d": round(ma10d, 3),
            "ma20d": round(ma20d, 3),
            "ma5w": round(ma5w, 3),
            "ma10w": round(ma10w, 3),
            "ma20w": round(ma20w, 3),
            "dev20w": round(dev20w, 4),
            "ma5d_dev": round(ma5d_dev, 4),
            "vr20d": round(vr20d, 3),
        },
    }
    return decision


def run_pipeline() -> dict[str, Any]:
    """Run post-close decisions and persist results/state."""
    params = dict(_DEFAULT_PARAMS)
    today = datetime.now(tz=_CN_TZ).date()

    stocks = _load_watchlist_active()
    holdings = _load_holdings()
    state = _load_state()

    def _job(stock: dict[str, Any]) -> tuple[str, list[_KlineBar], list[_KlineBar]]:
        code = str(stock.get("code", "")).strip()
        return (
            code,
            _fetch_jrj_kline(code, "day", 180),
            _fetch_jrj_kline(code, "week", 80),
        )

    kline_map: dict[str, tuple[list[_KlineBar], list[_KlineBar]]] = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(stocks)))) as pool:
        futures = [pool.submit(_job, s) for s in stocks]
        for fut in futures:
            try:
                code, daily, weekly = fut.result()
                if code:
                    kline_map[code] = (daily, weekly)
            except Exception:
                logger.exception("K线任务执行失败")

    decisions: list[dict[str, Any]] = []
    for stock in stocks:
        code = str(stock.get("code", "")).strip()
        pair = kline_map.get(code)
        if not pair:
            continue
        decision = _build_decision(
            stock=stock,
            daily=pair[0],
            weekly=pair[1],
            holdings=holdings,
            state=state,
            today=today,
            params=params,
        )
        if decision is not None:
            decisions.append(decision)

    # Keep actionable items first for operator review.
    rank = {"exit": 0, "reduce": 1, "add": 2, "open": 3, "hold": 4}
    decisions.sort(key=lambda d: (rank.get(str(d.get("action")), 9), str(d.get("code"))))

    output = {
        "schema_version": _OUTPUT_SCHEMA_VERSION,
        "generated_at": datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "source": "watchlist",
        "source_run_id": load_latest_run_id(),
        "source_files": ["memory/watchlist.json", "broker_data/positions/*.json"],
        "priority": ["exit", "reduce", "add", "open"],
        "count": len(decisions),
        "decisions": decisions,
    }

    _SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(_OUTPUT_FILE, output)
    _save_state(state)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-close trading decision pipeline")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs")
    _ = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if _.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    result = run_pipeline()
    logger.info("post-close decisions generated: %d", result.get("count", 0))


if __name__ == "__main__":
    main()
