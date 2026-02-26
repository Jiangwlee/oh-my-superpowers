#!/usr/bin/env python3
"""交易复盘模块（trade_review）。

对比交易计划（decision_log）和实际执行（broker_account），识别交易瑕疵并生成结构化复盘结果。
首版实现优先保证稳定输出与可测试性；部分高级逻辑（如滞后判定）后续迭代。
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - 环境未安装时降级
    yaml = None

from ashare_data.fetchers.broker_account import fetch_broker_account, load_history
from ashare_data.fetchers.trend_scanner import fetch_jrj_daily_kline, fetch_jrj_minute_kline
from ashare_data.core.config import DECISION_LOG
from scripts.core import shared as shared_core

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))


def _now_cn_iso() -> str:
    return shared_core.now_cn_iso()


def _today_cn() -> str:
    return shared_core.today_cn()


def _safe_float(value: Any, default: float = 0.0) -> float:
    return shared_core.safe_float(value, default)


def _safe_int(value: Any, default: int = 0) -> int:
    return shared_core.safe_int(value, default)


def _norm_code(value: Any) -> str:
    return shared_core.norm_code(value)


def _order_direction(order: dict[str, Any]) -> str:
    raw = (
        str(
            order.get("direction")
            or order.get("bs_flag")
            or order.get("bs")
            or order.get("trade_type")
            or order.get("type")
            or ""
        )
        .strip()
        .lower()
    )
    if raw in {"buy", "b", "1", "买入", "买"}:
        return "buy"
    if raw in {"sell", "s", "2", "卖出", "卖"}:
        return "sell"
    if "买" in raw:
        return "buy"
    if "卖" in raw:
        return "sell"
    return raw or "unknown"


def _order_status(order: dict[str, Any]) -> str:
    return str(order.get("status") or order.get("order_status") or "").strip()


def _is_cancelled(order: dict[str, Any]) -> bool:
    return "撤" in _order_status(order)


def _is_filled(order: dict[str, Any]) -> bool:
    if _is_cancelled(order):
        return False
    status = _order_status(order)
    if not status:
        return True
    return ("成" in status) or ("filled" in status.lower())


def _order_price(order: dict[str, Any]) -> float:
    return _safe_float(
        order.get("price") or order.get("deal_price") or order.get("match_price")
    )


def _order_qty(order: dict[str, Any]) -> int:
    return _safe_int(
        order.get("deal_volume")
        or order.get("deal_amount")
        or order.get("amount")
        or order.get("qty")
        or order.get("volume")
        or order.get("match_qty")
    )


def _flaw(
    *,
    category: str,
    severity: str,
    code: str = "",
    name: str = "",
    message: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "category": category,
        "severity": severity,
        "code": code,
        "name": name,
        "message": message,
    }
    if detail:
        item["detail"] = detail
    return item


def _load_latest_decision(log_path: str, target_date: str) -> dict[str, Any] | None:
    """读取 decision_log.jsonl 最近一条记录，优先匹配 target_date。"""
    path = Path(log_path)
    if not path.exists():
        return None

    target_or_prev: dict[str, Any] | None = None
    latest_any: dict[str, Any] | None = None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                latest_any = rec
                rec_date = str(rec.get("as_of_date") or "")
                if rec_date and rec_date <= target_date:
                    target_or_prev = rec
    except Exception:
        logger.exception("读取 decision_log 失败: %s", log_path)
        return None
    return target_or_prev or latest_any


def _load_strategy(yaml_path: str) -> dict[str, Any]:
    """读取 active.yaml。缺失或解析失败时返回默认值。"""
    return shared_core.load_strategy(yaml_path, logger=logger)


def _extract_pct_limit(text: str, fallback: float) -> float:
    """从类似“单只不超过总仓位20%”或“15%”的文本中提取比例。"""
    return shared_core.extract_pct_limit(text, fallback)


def _parse_range_to_pct(text: str) -> tuple[float, float] | None:
    """解析仓位区间文本，返回百分比数值（0-100）。"""
    return shared_core.parse_range_to_pct(text)


def _parse_position_limits(strategy: dict[str, Any]) -> dict[str, Any]:
    trend = (
        strategy.get("trend_stock")
        if isinstance(strategy.get("trend_stock"), dict)
        else {}
    )
    theme = (
        strategy.get("theme_stock")
        if isinstance(strategy.get("theme_stock"), dict)
        else {}
    )
    market_pos = (
        strategy.get("market_position")
        if isinstance(strategy.get("market_position"), dict)
        else {}
    )
    return {
        "max_single_trend": _extract_pct_limit(str(trend.get("position", "")), 0.20),
        "max_single_theme": _extract_pct_limit(str(theme.get("position", "")), 0.15),
        "market_ranges": {
            "strong": _parse_range_to_pct(str(market_pos.get("strong", "60-80%"))),
            "neutral": _parse_range_to_pct(str(market_pos.get("neutral", "30-50%"))),
            "weak": _parse_range_to_pct(str(market_pos.get("weak", "10-20%"))),
        },
    }


def _determine_account_mode(total: float, hold_earn: float) -> str:
    """根据账户盈亏比例判断账户模式（首版无滞后逻辑）。"""
    return shared_core.determine_account_mode(total, hold_earn)


def _candidate_map(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in candidates:
        if not isinstance(c, dict):
            continue
        code = _norm_code(c.get("code"))
        if code:
            out[code] = c
    return out


def _filled_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        o
        for o in orders
        if isinstance(o, dict) and not _is_cancelled(o) and _is_filled(o)
    ]


def _check_unplanned_trades(
    orders: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """检测计划外买入和观察股误买。"""
    flaws: list[dict[str, Any]] = []
    cand_map = _candidate_map(candidates)
    no_plan = len(cand_map) == 0

    for order in orders:
        if not isinstance(order, dict) or _is_cancelled(order):
            continue
        if _order_direction(order) != "buy":
            continue
        code = _norm_code(order.get("code"))
        name = str(order.get("name") or "")
        qty = _order_qty(order)
        price = _order_price(order)

        if no_plan:
            flaws.append(
                _flaw(
                    category="unplanned_trade",
                    severity="info",
                    code=code,
                    name=name,
                    message="无交易计划日的买入",
                    detail={"buy_price": price, "buy_amount": qty},
                )
            )
            continue

        cand = cand_map.get(code)
        if not cand:
            flaws.append(
                _flaw(
                    category="unplanned_trade",
                    severity="warning",
                    code=code,
                    name=name,
                    message="计划外买入: 该股不在当日推荐列表中",
                    detail={"buy_price": price, "buy_amount": qty},
                )
            )
            continue
        if str(cand.get("action") or "watch") == "watch":
            flaws.append(
                _flaw(
                    category="unplanned_trade",
                    severity="warning",
                    code=code,
                    name=name or str(cand.get("name") or ""),
                    message="观察股误买: 推荐为 watch 但实际执行买入",
                    detail={"buy_price": price, "buy_amount": qty},
                )
            )
    return flaws


def _check_missed_execution(
    orders: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    positions: dict[str, Any],
) -> list[dict[str, Any]]:
    """检测推荐买入未执行。"""
    flaws: list[dict[str, Any]] = []
    filled_buys = {
        _norm_code(o.get("code"))
        for o in orders
        if isinstance(o, dict) and _order_direction(o) == "buy" and not _is_cancelled(o)
    }
    hold_list = positions.get("hold_list") if isinstance(positions, dict) else []
    held_codes = {
        _norm_code(p.get("code"))
        for p in (hold_list if isinstance(hold_list, list) else [])
        if isinstance(p, dict)
    }
    for cand in candidates:
        if not isinstance(cand, dict) or str(cand.get("action") or "") != "buy":
            continue
        code = _norm_code(cand.get("code"))
        if not code or code in filled_buys or code in held_codes:
            continue
        score = _safe_float(cand.get("score"))
        severity = "warning" if score >= 80 else "info"
        flaws.append(
            _flaw(
                category="missed_execution",
                severity=severity,
                code=code,
                name=str(cand.get("name") or ""),
                message="推荐买入未执行",
                detail={"score": score},
            )
        )
    return flaws


def _calc_vwap(minute_bars: list[dict[str, Any]]) -> float:
    amount_sum = 0.0
    volume_sum = 0.0
    avg_values: list[float] = []
    for bar in minute_bars:
        amount_sum += _safe_float(bar.get("amount"))
        volume_sum += _safe_float(bar.get("volume"))
        avg = _safe_float(bar.get("avg"))
        if avg > 0:
            avg_values.append(avg)
    if amount_sum > 0 and volume_sum > 0:
        raw = amount_sum / volume_sum
        # JRJ llValue 常见口径为金额放大 10000 倍，做量级自适应避免 VWAP 偏大。
        return raw / 10000.0 if raw > 1000 else raw
    if avg_values:
        return sum(avg_values) / len(avg_values)
    return 0.0


def _timing_grade(direction: str, pos_pct: float) -> str:
    if direction == "buy":
        if pos_pct > 0.80:
            return "D"
        if pos_pct > 0.67:
            return "C"
        if pos_pct > 0.33:
            return "B"
        return "A"
    if pos_pct < 0.20:
        return "D"
    if pos_pct < 0.33:
        return "C"
    if pos_pct < 0.67:
        return "B"
    return "A"


def _analyze_timing(
    orders: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """分析成交委托的日内择时质量，输出 flaw 和 timing_score。"""
    flaws: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    filled = _filled_orders(orders)

    # 先按 code 去重并并发拉取分钟K线，避免同股多笔委托重复请求。
    minute_map: dict[str, list[dict[str, Any]]] = {}
    codes = sorted(
        {_norm_code(o.get("code")) for o in filled if _norm_code(o.get("code"))}
    )
    if codes:
        with ThreadPoolExecutor(max_workers=min(8, len(codes))) as pool:
            futs = {pool.submit(fetch_jrj_minute_kline, code): code for code in codes}
            for fut in as_completed(futs):
                code = futs[fut]
                try:
                    minute_map[code] = fut.result() or []
                except Exception:
                    logger.exception("获取分钟K失败: %s", code)
                    minute_map[code] = []

    for order in filled:
        direction = _order_direction(order)
        if direction not in {"buy", "sell"}:
            continue
        code = _norm_code(order.get("code"))
        name = str(order.get("name") or "")
        price = _order_price(order)
        minute_bars = minute_map.get(code, [])
        if not minute_bars:
            flaws.append(
                _flaw(
                    category="timing_flaw",
                    severity="info",
                    code=code,
                    name=name,
                    message="K线数据缺失: 跳过择时分析",
                )
            )
            continue

        day_low = min(_safe_float(x.get("low"), price) for x in minute_bars)
        day_high = max(_safe_float(x.get("high"), price) for x in minute_bars)
        if day_high <= day_low:
            pos_pct = 0.5
        else:
            pos_pct = (price - day_low) / (day_high - day_low)
        pos_pct = max(0.0, min(1.0, pos_pct))
        vwap = _calc_vwap(minute_bars)
        vs_vwap_pct = ((price - vwap) / vwap * 100.0) if vwap > 0 else 0.0
        grade = _timing_grade(direction, pos_pct)

        scores.append(
            {
                "code": code,
                "name": name,
                "direction": direction,
                "price": round(price, 4),
                "vwap": round(vwap, 4),
                "day_high": round(day_high, 4),
                "day_low": round(day_low, 4),
                "position_pct": round(pos_pct, 4),
                "vs_vwap_pct": round(vs_vwap_pct, 2),
                "grade": grade,
            }
        )

        if direction == "buy":
            if pos_pct > 0.80:
                flaws.append(
                    _flaw(
                        category="timing_flaw",
                        severity="error",
                        code=code,
                        name=name,
                        message="严重追高",
                    )
                )
            elif pos_pct > 0.67:
                flaws.append(
                    _flaw(
                        category="timing_flaw",
                        severity="warning",
                        code=code,
                        name=name,
                        message="追高买入",
                    )
                )
            if vwap > 0 and price > vwap * 1.02:
                flaws.append(
                    _flaw(
                        category="timing_flaw",
                        severity="info",
                        code=code,
                        name=name,
                        message="买入价高于VWAP 2%+",
                        detail={"vs_vwap_pct": round(vs_vwap_pct, 2)},
                    )
                )
        else:
            if pos_pct < 0.20:
                flaws.append(
                    _flaw(
                        category="timing_flaw",
                        severity="error",
                        code=code,
                        name=name,
                        message="严重恐慌卖出",
                    )
                )
            elif pos_pct < 0.33:
                flaws.append(
                    _flaw(
                        category="timing_flaw",
                        severity="warning",
                        code=code,
                        name=name,
                        message="恐慌卖出",
                    )
                )
            if vwap > 0 and price < vwap * 0.98:
                flaws.append(
                    _flaw(
                        category="timing_flaw",
                        severity="info",
                        code=code,
                        name=name,
                        message="卖出价低于VWAP 2%+",
                        detail={"vs_vwap_pct": round(vs_vwap_pct, 2)},
                    )
                )
    return flaws, scores


def _position_market_value(pos: dict[str, Any]) -> float:
    return shared_core.position_market_value(pos)


def _enrich_hold_list_prices(hold_list: list[dict[str, Any]]) -> None:
    """为缺少现价/市值的持仓补充日K线最新收盘价。

    JVQuant check_hold 只返回 code/name/hold_vol/hold_earn/day_earn，
    不含现价和市值。本函数通过 JRJ 日K线批量获取最新收盘价，
    并回填 last_price 和 market_value 到每个 position dict 中（原地修改）。
    """
    shared_core.enrich_hold_list_prices(
        hold_list,
        fetch_daily_kline=fetch_jrj_daily_kline,
        logger=logger,
    )


def _check_position_compliance(
    positions: dict[str, Any], strategy: dict[str, Any], regime: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """检测单股仓位和总仓位合规性。"""
    flaws: list[dict[str, Any]] = []
    limits = _parse_position_limits(strategy)

    total_assets = _safe_float(positions.get("total"))
    usable_cash = _safe_float(positions.get("usable"))
    hold_earn = _safe_float(positions.get("hold_earn"))
    hold_list = (
        positions.get("hold_list")
        if isinstance(positions.get("hold_list"), list)
        else []
    )

    total_position_pct = (
        ((total_assets - usable_cash) / total_assets * 100.0)
        if total_assets > 0
        else 0.0
    )
    account_mode = _determine_account_mode(total_assets, hold_earn)
    account_pnl_pct = (hold_earn / total_assets * 100.0) if total_assets > 0 else 0.0

    max_single_pct = 0.0
    max_single_name = ""
    single_limit = limits.get("max_single_trend", 0.20)
    for pos in hold_list:
        if not isinstance(pos, dict) or total_assets <= 0:
            continue
        mv = _position_market_value(pos)
        single_pct = mv / total_assets
        if single_pct > max_single_pct:
            max_single_pct = single_pct
            max_single_name = str(pos.get("name") or pos.get("stock_name") or "")
        if single_pct > 0.30:
            flaws.append(
                _flaw(
                    category="position_flaw",
                    severity="error",
                    code=_norm_code(pos.get("code")),
                    name=str(pos.get("name") or ""),
                    message="单股仓位超限",
                    detail={"single_pct": round(single_pct * 100, 2)},
                )
            )
        elif single_pct > single_limit:
            flaws.append(
                _flaw(
                    category="position_flaw",
                    severity="warning",
                    code=_norm_code(pos.get("code")),
                    name=str(pos.get("name") or ""),
                    message="单股仓位超限",
                    detail={"single_pct": round(single_pct * 100, 2)},
                )
            )

    market_ranges = limits.get("market_ranges", {})
    regime_range = (
        market_ranges.get(regime) if isinstance(market_ranges, dict) else None
    )
    regime_range_label = ""
    if isinstance(regime_range, tuple):
        regime_range_label = f"{int(regime_range[0])}-{int(regime_range[1])}%"
        if total_position_pct > regime_range[1] and not (
            regime == "weak" and total_position_pct > 30
        ):
            flaws.append(
                _flaw(
                    category="position_flaw",
                    severity="warning",
                    message=f"{regime} 市仓位过高",
                    detail={
                        "regime": regime,
                        "position_pct": round(total_position_pct, 2),
                        "range": regime_range_label,
                    },
                )
            )

    if regime == "weak" and total_position_pct > 30:
        flaws.append(
            _flaw(
                category="position_flaw",
                severity="warning",
                message="弱市重仓",
                detail={"position_pct": round(total_position_pct, 2)},
            )
        )

    if account_mode == "defensive" and total_position_pct > 50:
        flaws.append(
            _flaw(
                category="position_flaw",
                severity="warning",
                message="防御模式仓位过高",
                detail={"position_pct": round(total_position_pct, 2)},
            )
        )
    if account_mode == "critical" and hold_list:
        flaws.append(
            _flaw(
                category="position_flaw",
                severity="error",
                message="危急模式仍有持仓",
                detail={"position_count": len(hold_list)},
            )
        )

    check = {
        "total_assets": round(total_assets, 2),
        "usable_cash": round(usable_cash, 2),
        "total_position_pct": round(total_position_pct, 2),
        "market_regime": regime or "neutral",
        "account_mode": account_mode,
        "account_pnl_pct": round(account_pnl_pct, 2),
        "regime_position_range": regime_range_label,
        "single_stock_max_pct": round(max_single_pct * 100, 2),
        "single_stock_max_name": max_single_name,
        "compliant": not any(
            f["category"] == "position_flaw" and f["severity"] in {"warning", "error"}
            for f in flaws
        ),
    }
    return flaws, check


def _holding_days_from_history(code: str, history: dict[str, Any]) -> int:
    return shared_core.holding_days_from_history(code, history)


def _below_ma20_streak_from_history(
    code: str, current_price: float, history: dict[str, Any], ma20: float
) -> int:
    if ma20 <= 0:
        return 0
    streak = 1 if current_price < ma20 else 0
    positions_map = history.get("positions") if isinstance(history, dict) else {}
    if not isinstance(positions_map, dict):
        return streak
    for date in sorted(positions_map.keys(), reverse=True):
        snap = positions_map.get(date)
        hold_list = snap.get("hold_list") if isinstance(snap, dict) else []
        for pos in hold_list if isinstance(hold_list, list) else []:
            if not isinstance(pos, dict) or _norm_code(pos.get("code")) != code:
                continue
            px = _safe_float(
                pos.get("price") or pos.get("last_price") or pos.get("current_price")
            )
            if px <= 0:
                return streak
            if px < ma20:
                streak += 1
            else:
                return streak
            break
    return streak


def _check_holding_management(
    hold_list: list[dict[str, Any]], history: dict[str, Any]
) -> list[dict[str, Any]]:
    """检测持仓管理瑕疵（MA20 止损 / MA5 乖离 / 持续亏损持仓）。"""
    flaws: list[dict[str, Any]] = []
    if not hold_list:
        return flaws

    codes = [_norm_code(h.get("code")) for h in hold_list if isinstance(h, dict)]
    daily_map: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(codes)))) as pool:
        futs = {
            pool.submit(fetch_jrj_daily_kline, code, 30): code for code in codes if code
        }
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                daily_map[code] = fut.result() or []
            except Exception:
                logger.exception("获取日K失败: %s", code)
                daily_map[code] = []

    for pos in hold_list:
        if not isinstance(pos, dict):
            continue
        code = _norm_code(pos.get("code"))
        name = str(pos.get("name") or "")
        bars = daily_map.get(code, [])
        closes = [
            _safe_float(x.get("close")) for x in bars if _safe_float(x.get("close")) > 0
        ]
        current_price = _safe_float(
            pos.get("price") or pos.get("last_price") or pos.get("current_price")
        )
        if current_price <= 0 and closes:
            current_price = closes[-1]
        if len(closes) < 20 or current_price <= 0:
            continue

        ma20 = sum(closes[-20:]) / 20.0
        ma5 = sum(closes[-5:]) / 5.0 if len(closes) >= 5 else 0.0
        below_streak = _below_ma20_streak_from_history(
            code, current_price, history, ma20
        )
        if below_streak >= 3:
            flaws.append(
                _flaw(
                    category="holding_flaw",
                    severity="error",
                    code=code,
                    name=name,
                    message="未执行MA20止损",
                    detail={"below_ma20_days": below_streak},
                )
            )
        elif below_streak >= 1:
            flaws.append(
                _flaw(
                    category="holding_flaw",
                    severity="info",
                    code=code,
                    name=name,
                    message="逼近MA20止损线",
                    detail={"below_ma20_days": below_streak},
                )
            )

        if ma5 > 0:
            deviation = (current_price - ma5) / ma5
            if deviation > 0.20:
                flaws.append(
                    _flaw(
                        category="holding_flaw",
                        severity="error",
                        code=code,
                        name=name,
                        message="偏离MA5超20%未减仓",
                        detail={"deviation_pct": round(deviation * 100, 2)},
                    )
                )
            elif deviation > 0.15:
                flaws.append(
                    _flaw(
                        category="holding_flaw",
                        severity="warning",
                        code=code,
                        name=name,
                        message="偏离MA5超15%未减仓",
                        detail={"deviation_pct": round(deviation * 100, 2)},
                    )
                )

        hold_earn_pct = _safe_float(pos.get("hold_earn_pct"))
        if hold_earn_pct == 0:
            cost = _safe_float(pos.get("cost_price"))
            if cost > 0:
                hold_earn_pct = (current_price - cost) / cost * 100.0
        if hold_earn_pct < -10 and _holding_days_from_history(code, history) > 5:
            flaws.append(
                _flaw(
                    category="holding_flaw",
                    severity="warning",
                    code=code,
                    name=name,
                    message="持续亏损持仓未处理",
                    detail={"hold_earn_pct": round(hold_earn_pct, 2)},
                )
            )

    return flaws


def _check_discipline(
    orders: list[dict[str, Any]], account_mode: str, history: dict[str, Any]
) -> list[dict[str, Any]]:
    """检测纪律执行瑕疵。"""
    flaws: list[dict[str, Any]] = []
    if account_mode in {"defensive", "critical"}:
        has_buy = any(
            _order_direction(o) == "buy" and not _is_cancelled(o)
            for o in orders
            if isinstance(o, dict)
        )
        if has_buy:
            flaws.append(
                _flaw(
                    category="discipline_flaw",
                    severity="error",
                    message="防御模式下加仓"
                    if account_mode == "defensive"
                    else "危急模式下仍加仓",
                    detail={"account_mode": account_mode},
                )
            )

    # 最近 3 天翻转交易检测（历史窗口），随后会合并当日 orders。
    # 即实际判断语义为“含当日 + 最近若干历史记录”的组合窗口。
    history_orders = history.get("orders") if isinstance(history, dict) else {}
    recent_codes: dict[str, set[str]] = {}
    if isinstance(history_orders, dict):
        for _, snapshot in sorted(history_orders.items(), reverse=True)[:3]:
            order_list = (
                snapshot.get("order_list") if isinstance(snapshot, dict) else []
            )
            for o in order_list if isinstance(order_list, list) else []:
                if not isinstance(o, dict) or _is_cancelled(o):
                    continue
                code = _norm_code(o.get("code"))
                if not code:
                    continue
                recent_codes.setdefault(code, set()).add(_order_direction(o))
    for o in orders:
        if not isinstance(o, dict) or _is_cancelled(o):
            continue
        code = _norm_code(o.get("code"))
        if code:
            recent_codes.setdefault(code, set()).add(_order_direction(o))
    for code, dirs in recent_codes.items():
        if "buy" in dirs and "sell" in dirs:
            flaws.append(
                _flaw(
                    category="discipline_flaw",
                    severity="warning",
                    code=code,
                    message="频繁翻转交易",
                )
            )

    current_hold_list = (
        history.get("current_hold_list") if isinstance(history, dict) else None
    )
    if isinstance(current_hold_list, list) and len(current_hold_list) > 8:
        flaws.append(
            _flaw(
                category="discipline_flaw",
                severity="info",
                message="持仓过于分散",
                detail={"position_count": len(current_hold_list)},
            )
        )
    return flaws


def _count_flaws(flaws: list[dict[str, Any]]) -> dict[str, Any]:
    out = {
        "error": 0,
        "warning": 0,
        "info": 0,
        "total": 0,
        "by_category": {
            "unplanned_trade": 0,
            "missed_execution": 0,
            "timing_flaw": 0,
            "position_flaw": 0,
            "holding_flaw": 0,
            "discipline_flaw": 0,
        },
    }
    for f in flaws:
        sev = str(f.get("severity") or "")
        cat = str(f.get("category") or "")
        if sev in out:
            out[sev] += 1
        if cat in out["by_category"]:
            out["by_category"][cat] += 1
    out["total"] = out["error"] + out["warning"] + out["info"]
    return out


def _generate_suggestions(
    flaws: list[dict[str, Any]], timing_scores: list[dict[str, Any]]
) -> list[str]:
    suggestions: list[str] = []
    unplanned = [f for f in flaws if f.get("category") == "unplanned_trade"]
    if unplanned:
        suggestions.append(
            f"当日存在{len(unplanned)}笔计划偏离买入，建议严格按推荐列表执行"
        )
    holding = [
        f
        for f in flaws
        if f.get("category") == "holding_flaw" and "MA20" in str(f.get("message"))
    ]
    if holding:
        target = holding[0]
        if target.get("name"):
            suggestions.append(
                f"持仓「{target['name']}」触发 MA20 风险提示，明日优先检查止损纪律"
            )
    low_grades = [s for s in timing_scores if s.get("grade") in {"C", "D"}]
    if low_grades:
        suggestions.append(
            f"择时评分较弱交易 {len(low_grades)} 笔，建议复盘分时位置与 VWAP 偏离"
        )
    if not suggestions:
        suggestions.append("当日执行整体较为合规，继续保持并跟踪下一交易日反馈")
    return suggestions[:5]


def _append_evolution_feedback(result: dict[str, Any], base_dir: Path) -> None:
    """追加简要反馈到 evolution/feedback.md（失败不影响主流程）。"""
    try:
        evo_dir = base_dir / "evolution"
        evo_dir.mkdir(parents=True, exist_ok=True)
        feedback = evo_dir / "feedback.md"
        flaws = result.get("flaw_counts", {})
        timing_scores = result.get("timing_scores", [])
        buy_grades = [
            s.get("grade")
            for s in timing_scores
            if s.get("direction") == "buy" and s.get("grade")
        ]
        sell_grades = [
            s.get("grade")
            for s in timing_scores
            if s.get("direction") == "sell" and s.get("grade")
        ]
        buy_avg = Counter(buy_grades).most_common(1)[0][0] if buy_grades else "-"
        sell_avg = Counter(sell_grades).most_common(1)[0][0] if sell_grades else "-"
        lines = [
            "",
            f"{result.get('review_date')} 交易复盘",
            f"- 瑕疵: {flaws.get('error', 0)} error / {flaws.get('warning', 0)} warning / {flaws.get('info', 0)} info",
            f"- 择时评分: 买入均分 {buy_avg}, 卖出均分 {sell_avg}",
            f"- 仓位合规: {'通过' if result.get('position_check', {}).get('compliant') else '未通过'}",
        ]
        major = next(
            (
                f
                for f in result.get("flaws", [])
                if f.get("severity") in {"error", "warning"}
            ),
            None,
        )
        if isinstance(major, dict):
            lines.append(f"- 关键问题: {major.get('message')}")
        with feedback.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except Exception:
        logger.exception("追加 evolution/feedback.md 失败")


def run_trade_review(
    broker_data: dict[str, Any] | None = None,
    decision_log_path: str = str(DECISION_LOG),
    strategy_path: str = "strategy/active.yaml",
    output_path: str = "trade_review.json",
) -> dict[str, Any]:
    """执行交易复盘并写出 trade_review.json。"""
    if broker_data is None:
        try:
            broker_data = fetch_broker_account()
        except Exception as exc:
            logger.exception("broker_account 获取失败")
            return {"error": "broker_data_unavailable", "message": str(exc)}

    if not isinstance(broker_data, dict):
        return {"error": "broker_data_unavailable"}

    review_date = (
        str(broker_data.get("date") or "")
        or str(broker_data.get("fetched_at") or "")[:10]
        or _today_cn()
    )
    strategy = _load_strategy(strategy_path)
    decision = _load_latest_decision(decision_log_path, review_date)
    history = load_history(days=5)
    history["current_hold_list"] = broker_data.get("hold_list", [])

    orders = (
        broker_data.get("order_list")
        if isinstance(broker_data.get("order_list"), list)
        else []
    )
    positions = {
        "total": broker_data.get("total", 0),
        "usable": broker_data.get("usable", 0),
        "day_earn": broker_data.get("day_earn", 0),
        "hold_earn": broker_data.get("hold_earn", 0),
        "hold_list": broker_data.get("hold_list", []),
    }
    candidates = decision.get("candidates", []) if isinstance(decision, dict) else []
    regime = (
        str(decision.get("market_regime") or "neutral")
        if isinstance(decision, dict)
        else "neutral"
    )

    unplanned_flaws = _check_unplanned_trades(orders, candidates)
    missed_flaws = (
        _check_missed_execution(orders, candidates, positions) if candidates else []
    )
    timing_flaws, timing_scores = _analyze_timing(orders) if orders else ([], [])

    # 补充现价/市值（JVQuant hold_list 不含此信息）
    _enrich_hold_list_prices(positions.get("hold_list", []))

    position_flaws, position_check = _check_position_compliance(
        positions, strategy, regime
    )
    holding_flaws = _check_holding_management(positions.get("hold_list", []), history)
    account_mode = position_check.get("account_mode", "normal")
    discipline_flaws = _check_discipline(orders, str(account_mode), history)

    flaws = (
        unplanned_flaws
        + missed_flaws
        + timing_flaws
        + position_flaws
        + holding_flaws
        + discipline_flaws
    )
    flaw_counts = _count_flaws(flaws)

    filled_orders = _filled_orders(orders)
    buy_orders = [
        o for o in orders if _order_direction(o) == "buy" and not _is_cancelled(o)
    ]
    sell_orders = [
        o for o in orders if _order_direction(o) == "sell" and not _is_cancelled(o)
    ]
    cancelled_orders = [o for o in orders if _is_cancelled(o)]
    unplanned_buys = [
        f for f in unplanned_flaws if f.get("severity") in {"info", "warning", "error"}
    ]
    planned_buys = max(0, len(buy_orders) - len(unplanned_buys))
    missed_buys = len(
        [f for f in missed_flaws if f.get("category") == "missed_execution"]
    )
    plan_match_rate = (planned_buys / len(buy_orders) * 100.0) if buy_orders else 100.0

    total_assets = _safe_float(positions.get("total"))
    usable_cash = _safe_float(positions.get("usable"))
    hold_earn = _safe_float(positions.get("hold_earn"))
    expected_timing_orders = sum(
        1 for o in filled_orders if _order_direction(o) in {"buy", "sell"}
    )
    minute_kline_ok = len(timing_scores) >= expected_timing_orders

    result = {
        "review_date": review_date,
        "generated_at": _now_cn_iso(),
        "account_snapshot": {
            "total_assets": round(total_assets, 2),
            "usable_cash": round(usable_cash, 2),
            "day_earn": round(_safe_float(positions.get("day_earn")), 2),
            "hold_earn": round(hold_earn, 2),
            "position_count": len(positions.get("hold_list", [])),
            "account_mode": account_mode,
            "account_pnl_pct": round(
                (hold_earn / total_assets * 100.0) if total_assets > 0 else 0.0, 2
            ),
        },
        "execution_summary": {
            "total_orders": len(orders),
            "buy_orders": len(buy_orders),
            "sell_orders": len(sell_orders),
            "cancelled_orders": len(cancelled_orders),
            "planned_buys": planned_buys,
            "unplanned_buys": len(unplanned_buys),
            "missed_buys": missed_buys,
            "plan_match_rate": round(plan_match_rate, 1),
        },
        "flaws": flaws,
        "timing_scores": timing_scores,
        "position_check": position_check,
        "flaw_counts": flaw_counts,
        "improvement_suggestions": _generate_suggestions(flaws, timing_scores),
        "metadata": {
            "strategy_version": strategy.get("strategy_version", "unknown"),
            "decision_log_date": decision.get("as_of_date")
            if isinstance(decision, dict)
            else None,
            "decision_log_run_id": decision.get("run_id")
            if isinstance(decision, dict)
            else None,
            "data_completeness": {
                "broker_data": True,
                "decision_log": bool(decision),
                "minute_kline": minute_kline_ok,
                "daily_kline": True,
            },
        },
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _append_evolution_feedback(result, out_path.parent)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="交易复盘模块")
    parser.add_argument("--decision-log", default=str(DECISION_LOG))
    parser.add_argument("--strategy", default="strategy/active.yaml")
    parser.add_argument("--output", default="trade_review.json")
    parser.add_argument("--pretty", action="store_true", help="打印格式化 JSON")
    args = parser.parse_args()

    result = run_trade_review(
        decision_log_path=args.decision_log,
        strategy_path=args.strategy,
        output_path=args.output,
    )
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {"ok": "error" not in result, "output": args.output}, ensure_ascii=False
            )
        )


if __name__ == "__main__":
    main()
