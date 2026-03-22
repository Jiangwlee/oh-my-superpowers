"""Build retained market/theme emotion facts from THS history."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Callable

from ashare_data.fetchers.market_breadth import MarketBreadth, fetch_market_breadth_for_date
from ashare_data.fetchers.market_sentiment import fetch_market_sentiment_for_date
from ashare_data.fetchers.market_turnover import MarketTurnover, fetch_market_turnover_for_date
from ashare_data.fetchers.trend_scanner import fetch_ths_history

from app.core.runtime import build_run_id
from app.db.session import init_db, open_session
from app.repositories.emotion_fact_repository import replace_for_date


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _delta(current: int | None, previous: int | None) -> int | None:
    if current is None or previous is None:
        return None
    return current - previous


def _mean(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 4)


def _market_cycle_hint(highest_board: int, board_ge_3_count: int, risk_score: float) -> str:
    if risk_score >= 6.0:
        return "cooling"
    if highest_board >= 7 and board_ge_3_count >= 5:
        return "peak"
    if highest_board >= 5 and board_ge_3_count >= 2:
        return "expanding"
    if highest_board >= 3:
        return "warming"
    return "ice"


def _theme_cycle_hint(limit_up_num: int, leader_board_max: int, limit_up_num_3d_delta: int | None) -> str:
    if leader_board_max >= 5 and limit_up_num_3d_delta is not None and limit_up_num_3d_delta < 0:
        return "bad_divergence"
    if leader_board_max >= 5 and limit_up_num >= 10:
        return "climax"
    if leader_board_max >= 4 and limit_up_num >= 6:
        return "main_rise"
    if leader_board_max >= 2 and limit_up_num >= 3:
        return "ferment"
    return "start"


def _board_count_from_history_label(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    text = str(value).strip()
    if not text or text == "--":
        return None
    if "首板" in text:
        return 1
    if "天" in text and "板" in text:
        try:
            return int(text.split("天", 1)[1].split("板", 1)[0])
        except (TypeError, ValueError):
            return None
    return None


def _continuous_board_map(day: dict[str, Any]) -> dict[str, int]:
    board_map: dict[str, int] = {}
    for item in day.get("continuous_limit_up") or []:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        board_map[code] = _safe_int(item.get("continue_num"), 1)
    for theme in day.get("block_top") or []:
        for stock in theme.get("stock_list") or []:
            code = str(stock.get("code") or "").strip()
            if not code or code in board_map:
                continue
            board_count = _board_count_from_history_label(stock.get("high_days"))
            if board_count is None:
                board_count = _safe_int(stock.get("continue_num"), 0) or None
            if board_count is not None:
                board_map[code] = board_count
    return board_map


def _promotion_stats(previous_day: dict[str, Any] | None, current_day: dict[str, Any]) -> dict[str, Any]:
    if previous_day is None:
        return {
            "promotion_2to3_total": None,
            "promotion_2to3_success": None,
            "promotion_3to4_total": None,
            "promotion_3to4_success": None,
            "promotion_candidates_2to3": [],
            "promotion_candidates_3to4": [],
        }

    previous_boards = _continuous_board_map(previous_day)
    current_boards = _continuous_board_map(current_day)
    candidates_2to3 = sorted(code for code, board in previous_boards.items() if board == 2)
    candidates_3to4 = sorted(code for code, board in previous_boards.items() if board == 3)
    success_2to3 = sum(1 for code in candidates_2to3 if current_boards.get(code, 0) >= 3)
    success_3to4 = sum(1 for code in candidates_3to4 if current_boards.get(code, 0) >= 4)
    return {
        "promotion_2to3_total": len(candidates_2to3),
        "promotion_2to3_success": success_2to3,
        "promotion_3to4_total": len(candidates_3to4),
        "promotion_3to4_success": success_3to4,
        "promotion_candidates_2to3": candidates_2to3,
        "promotion_candidates_3to4": candidates_3to4,
    }


def _extract_market_stats(day: dict[str, Any]) -> dict[str, Any]:
    ladder = day.get("continuous_limit_up") or []
    heights = [_safe_int(item.get("continue_num"), 1) for item in ladder]
    block_top = day.get("block_top") or []
    top_theme = block_top[0] if block_top else {}
    return {
        "highest_board": max(heights) if heights else 0,
        "limit_up_ladder_count": len(heights),
        "board_ge_2_count": sum(1 for height in heights if height >= 2),
        "board_ge_3_count": sum(1 for height in heights if height >= 3),
        "board_ge_4_count": sum(1 for height in heights if height >= 4),
        "theme_count": len(block_top),
        "top_theme_name": top_theme.get("name"),
        "top_theme_limit_up_num": _safe_int(top_theme.get("limit_up_num")) if top_theme else None,
    }


def _theme_rows_by_date(history: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, dict[str, Any]]] = {}
    for day in history:
        daily: dict[str, dict[str, Any]] = {}
        for idx, theme in enumerate(day.get("block_top") or [], start=1):
            stock_list = theme.get("stock_list") or []
            boards = [_safe_int(stock.get("continue_num"), 1) for stock in stock_list]
            daily[str(theme.get("name") or f"theme-{idx}")] = {
                "theme_rank": idx,
                "limit_up_num": _safe_int(theme.get("limit_up_num")),
                "theme_change_pct": _safe_float(theme.get("change")),
                "sample_stock_count": len(stock_list),
                "leader_names_json": [stock.get("name") for stock in stock_list if stock.get("name")],
                "leader_board_max": max(boards) if boards else 0,
                "leader_board_count_ge_2": sum(1 for board in boards if board >= 2),
                "first_limit_count": sum(1 for stock in stock_list if stock.get("change_tag") == "FIRST_LIMIT"),
                "limit_back_count": sum(1 for stock in stock_list if stock.get("change_tag") == "LIMIT_BACK"),
                "high_limit_count": sum(1 for stock in stock_list if stock.get("change_tag") == "HIGH_LIMIT"),
                "evidence_json": {
                    "leaders": stock_list,
                    "theme_change_pct": _safe_float(theme.get("change")),
                },
            }
        rows[day["date"]] = daily
    return rows


def build_emotion_facts(
    *,
    trade_date: str,
    history_fetcher: Callable[..., list[dict[str, Any]]] = fetch_ths_history,
    sentiment_fetcher: Callable[[str], Any] = fetch_market_sentiment_for_date,
    breadth_fetcher: Callable[[str], MarketBreadth] = fetch_market_breadth_for_date,
    turnover_fetcher: Callable[[str], MarketTurnover] = fetch_market_turnover_for_date,
) -> dict[str, Any]:
    """Build and persist market/theme emotion rows for one trade date."""
    resolved_date = date.fromisoformat(trade_date)
    ths_date = resolved_date.strftime("%Y%m%d")
    run_id = build_run_id(trade_date, "build-emotion-facts")
    history = history_fetcher(days=30, end_date=ths_date) or []
    if not history:
        raise ValueError("No THS history available for emotion fact build")

    by_date = {day["date"]: _extract_market_stats(day) for day in history}
    ordered_dates = [day["date"] for day in history]
    current_key = ordered_dates[-1]
    current_stats = by_date[current_key]
    idx = len(ordered_dates) - 1
    previous_day = history[idx - 1] if idx >= 1 else None
    prev_3_key = ordered_dates[idx - 2] if idx >= 2 else None
    prev_5_key = ordered_dates[idx - 4] if idx >= 4 else None
    prev_3 = by_date.get(prev_3_key) if prev_3_key else None
    prev_5 = by_date.get(prev_5_key) if prev_5_key else None
    sentiment_by_date: dict[str, dict[str, Any]] = {}
    for date_key in ordered_dates:
        try:
            sentiment = sentiment_fetcher(date_key)
        except Exception:
            sentiment = None
        if isinstance(sentiment, dict):
            sentiment_by_date[date_key] = {
                "limit_up": _safe_int(sentiment.get("limit_up")) if sentiment.get("limit_up") is not None else None,
                "limit_down": _safe_int(sentiment.get("limit_down")) if sentiment.get("limit_down") is not None else None,
                "blowup_rate": _safe_float(sentiment.get("blowup_rate")),
                "seal_rate": _safe_float(sentiment.get("seal_rate")),
                "limit_up_history_num": _safe_int(sentiment.get("limit_up_history_num"))
                if sentiment.get("limit_up_history_num") is not None
                else None,
                "limit_up_open_num": _safe_int(sentiment.get("limit_up_open_num"))
                if sentiment.get("limit_up_open_num") is not None
                else None,
                "limit_down_history_num": _safe_int(sentiment.get("limit_down_history_num"))
                if sentiment.get("limit_down_history_num") is not None
                else None,
                "limit_down_open_num": _safe_int(sentiment.get("limit_down_open_num"))
                if sentiment.get("limit_down_open_num") is not None
                else None,
            }
        else:
            sentiment_by_date[date_key] = {
                "limit_up": _safe_int(getattr(sentiment, "limit_up", None))
                if getattr(sentiment, "limit_up", None) is not None
                else None,
                "limit_down": _safe_int(getattr(sentiment, "limit_down", None))
                if getattr(sentiment, "limit_down", None) is not None
                else None,
                "blowup_rate": _safe_float(getattr(sentiment, "blowup_rate", None)),
                "seal_rate": _safe_float(getattr(sentiment, "seal_rate", None)),
                "limit_up_history_num": _safe_int(getattr(sentiment, "limit_up_history_num", None))
                if getattr(sentiment, "limit_up_history_num", None) is not None
                else None,
                "limit_up_open_num": _safe_int(getattr(sentiment, "limit_up_open_num", None))
                if getattr(sentiment, "limit_up_open_num", None) is not None
                else None,
                "limit_down_history_num": _safe_int(getattr(sentiment, "limit_down_history_num", None))
                if getattr(sentiment, "limit_down_history_num", None) is not None
                else None,
                "limit_down_open_num": _safe_int(getattr(sentiment, "limit_down_open_num", None))
                if getattr(sentiment, "limit_down_open_num", None) is not None
                else None,
            }

    current_sentiment = sentiment_by_date.get(current_key, {})
    prev_3_sentiment = sentiment_by_date.get(prev_3_key, {}) if prev_3_key else {}
    breadth = breadth_fetcher(trade_date)
    turnover = turnover_fetcher(current_key)
    promotion_stats = _promotion_stats(previous_day, history[idx])

    heat_score = round(
        current_stats["highest_board"] * 1.2
        + current_stats["board_ge_3_count"] * 1.5
        + (current_stats["top_theme_limit_up_num"] or 0) * 0.4
        + float(current_sentiment.get("limit_up") or 0) * 0.05,
        4,
    )
    risk_score = round(
        float(current_stats["board_ge_4_count"]) * 1.5
        + float(current_sentiment.get("limit_down") or 0) * 0.2
        + float(current_sentiment.get("blowup_rate") or 0.0) * 10.0,
        4,
    )
    market_row = {
        "trade_date": resolved_date,
        "run_id": run_id,
        "source": "ths",
        "limit_up_count": current_sentiment.get("limit_up"),
        "limit_down_count": current_sentiment.get("limit_down"),
        "highest_board": current_stats["highest_board"],
        "limit_up_ladder_count": current_stats["limit_up_ladder_count"],
        "board_ge_2_count": current_stats["board_ge_2_count"],
        "board_ge_3_count": current_stats["board_ge_3_count"],
        "board_ge_4_count": current_stats["board_ge_4_count"],
        "advance_count": breadth.advance_count,
        "decline_count": breadth.decline_count,
        "flat_count": breadth.flat_count,
        "theme_count": current_stats["theme_count"],
        "top_theme_name": current_stats["top_theme_name"],
        "top_theme_limit_up_num": current_stats["top_theme_limit_up_num"],
        "blowup_rate": current_sentiment.get("blowup_rate"),
        "seal_rate": current_sentiment.get("seal_rate"),
        "promotion_2to3_total": promotion_stats["promotion_2to3_total"],
        "promotion_2to3_success": promotion_stats["promotion_2to3_success"],
        "promotion_3to4_total": promotion_stats["promotion_3to4_total"],
        "promotion_3to4_success": promotion_stats["promotion_3to4_success"],
        "market_volume": turnover.market_volume,
        "yesterday_limit_up_return": None,
        "highest_board_3d_delta": _delta(current_stats["highest_board"], prev_3["highest_board"] if prev_3 else None),
        "highest_board_5d_delta": _delta(current_stats["highest_board"], prev_5["highest_board"] if prev_5 else None),
        "board_ge_3_count_3d_delta": _delta(
            current_stats["board_ge_3_count"], prev_3["board_ge_3_count"] if prev_3 else None
        ),
        "board_ge_4_count_3d_delta": _delta(
            current_stats["board_ge_4_count"], prev_3["board_ge_4_count"] if prev_3 else None
        ),
        "limit_up_count_3d_delta": _delta(current_sentiment.get("limit_up"), prev_3_sentiment.get("limit_up")),
        "limit_down_count_3d_delta": _delta(
            current_sentiment.get("limit_down"), prev_3_sentiment.get("limit_down")
        ),
        "top_theme_limit_up_num_3d_delta": _delta(
            current_stats["top_theme_limit_up_num"], prev_3["top_theme_limit_up_num"] if prev_3 else None
        ),
        "heat_score": heat_score,
        "risk_score": risk_score,
        "emotion_score": round(heat_score - risk_score, 4),
        "cycle_stage_hint": _market_cycle_hint(
            current_stats["highest_board"], current_stats["board_ge_3_count"], risk_score
        ),
        "evidence_json": {
            "history_window_start": ordered_dates[0],
            "history_window_end": ordered_dates[-1],
            "market_breadth": {
                "zdfb_bins": breadth.zdfb_bins or [],
                "universe_total": breadth.universe_total,
            },
            "market_sentiment": {
                "limit_up_history_num": current_sentiment.get("limit_up_history_num"),
                "limit_up_open_num": current_sentiment.get("limit_up_open_num"),
                "limit_down_history_num": current_sentiment.get("limit_down_history_num"),
                "limit_down_open_num": current_sentiment.get("limit_down_open_num"),
            },
            "market_volume": {
                "source": "ths_turnover_day",
                "source_code": turnover.source_code,
                "source_name": turnover.source_name,
            },
            "promotion": {
                "candidates_2to3": promotion_stats["promotion_candidates_2to3"],
                "candidates_3to4": promotion_stats["promotion_candidates_3to4"],
            },
        },
    }

    theme_history = _theme_rows_by_date(history)
    current_theme_rows = theme_history[current_key]
    theme_rows: list[dict[str, Any]] = []
    for theme_name, current in current_theme_rows.items():
        theme_date_positions = [date_key for date_key in ordered_dates if theme_name in theme_history.get(date_key, {})]
        current_pos = theme_date_positions.index(current_key)
        prev_theme_3_key = theme_date_positions[current_pos - 2] if current_pos >= 2 else None
        prev_theme_5_key = theme_date_positions[current_pos - 4] if current_pos >= 4 else None
        prev_theme_3 = theme_history.get(prev_theme_3_key, {}).get(theme_name) if prev_theme_3_key else None
        prev_theme_5 = theme_history.get(prev_theme_5_key, {}).get(theme_name) if prev_theme_5_key else None
        recent_changes = []
        for date_key in theme_date_positions[max(0, current_pos - 2) : current_pos + 1]:
            recent_changes.append(theme_history[date_key][theme_name].get("theme_change_pct"))
        heat = round(
            current["limit_up_num"] * 1.2
            + current["leader_board_max"] * 1.5
            + current["leader_board_count_ge_2"] * 0.8,
            4,
        )
        risk = round(float(current["high_limit_count"]) * 1.2, 4)
        limit_up_num_3d_delta = _delta(
            current["limit_up_num"], prev_theme_3["limit_up_num"] if prev_theme_3 else None
        )
        theme_rows.append(
            {
                "trade_date": resolved_date,
                "run_id": run_id,
                "theme_name": theme_name,
                "theme_rank": current["theme_rank"],
                "source": "ths_block_top",
                "limit_up_num": current["limit_up_num"],
                "theme_change_pct": current["theme_change_pct"],
                "sample_stock_count": current["sample_stock_count"],
                "leader_names_json": current["leader_names_json"],
                "leader_board_max": current["leader_board_max"],
                "leader_board_count_ge_2": current["leader_board_count_ge_2"],
                "first_limit_count": current["first_limit_count"],
                "limit_back_count": current["limit_back_count"],
                "high_limit_count": current["high_limit_count"],
                "theme_rank_3d_delta": _delta(
                    current["theme_rank"], prev_theme_3["theme_rank"] if prev_theme_3 else None
                ),
                "limit_up_num_3d_delta": limit_up_num_3d_delta,
                "limit_up_num_5d_delta": _delta(
                    current["limit_up_num"], prev_theme_5["limit_up_num"] if prev_theme_5 else None
                ),
                "theme_change_3d_mean": _mean(recent_changes),
                "leader_board_max_3d_trend": _delta(
                    current["leader_board_max"], prev_theme_3["leader_board_max"] if prev_theme_3 else None
                ),
                "leader_continuity_score": round(
                    current["leader_board_max"] + current["leader_board_count_ge_2"] * 0.5,
                    4,
                ),
                "heat_score": heat,
                "risk_score": risk,
                "theme_cycle_hint": _theme_cycle_hint(
                    current["limit_up_num"], current["leader_board_max"], limit_up_num_3d_delta
                ),
                "evidence_json": current["evidence_json"],
            }
        )

    init_db()
    with open_session() as session:
        market_rows_written, theme_rows_written = replace_for_date(
            session, resolved_date, market_row, theme_rows
        )

    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "market_rows_written": market_rows_written,
        "theme_rows_written": theme_rows_written,
        "history_days_used": len(history),
    }
