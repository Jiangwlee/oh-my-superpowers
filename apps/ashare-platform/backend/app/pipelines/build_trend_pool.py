"""Trend pool build pipeline.

Purpose: Produce retained daily trend facts from deterministic scanner output.

Public API:
    build_trend_pool(...) -> dict
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from ashare_data.fetchers.trend_scanner import fetch_eastmoney_popularity_rank, scan_all

from app.core.runtime import build_run_id
from app.db.session import init_db, open_session
from app.repositories.trend_pool_repository import replace_for_date


def _to_row(trade_date: date, run_id: str, item: Any) -> dict[str, Any]:
    data = item.to_dict() if hasattr(item, "to_dict") else dict(item)
    return {
        "trade_date": trade_date,
        "run_id": run_id,
        "code": str(data.get("code", "")),
        "name": str(data.get("name", "")),
        "rank": int(data.get("rank", 0) or 0),
        "source": str(data.get("source", "")),
        "score_total": float(data.get("score_total_100", 0.0) or 0.0),
        "star_rating": int(data.get("star_rating", 0) or 0),
        "emotion_level": int(data.get("emotion_level", 0) or 0),
        "emotion_label": str(data.get("emotion_label", "")),
        "trade_signal": str(data.get("trade_signal", "")),
        "is_uptrend": bool(data.get("is_uptrend", False)),
        "gain_30_pct": float(data["gain_30_pct"]) if data.get("gain_30_pct") is not None else None,
        "gain_60_pct": float(data["gain_60_pct"]) if data.get("gain_60_pct") is not None else None,
        "holding_experience": str(data.get("holding_experience", "")) or None,
        "reason": str(data.get("reason", "")) or None,
        "tags_json": {
            "emotion_reason": data.get("emotion_reason"),
            "trade_signal_reason": data.get("trade_signal_reason"),
        },
    }


def build_trend_pool(
    *,
    trade_date: str,
    max_rank: int = 1000,
    fetch_candidates: Callable[..., list[dict[str, Any]]] = fetch_eastmoney_popularity_rank,
    scanner: Callable[..., list[Any]] = scan_all,
) -> dict[str, Any]:
    """Build and persist one day of trend pool facts."""
    resolved_date = date.fromisoformat(trade_date)
    run_id = build_run_id(trade_date, "build-trend-pool")
    candidates = fetch_candidates(top_n=max_rank)
    results = scanner(candidates)
    rows = [
        _to_row(resolved_date, run_id, item)
        for item in results
        if bool((item.to_dict() if hasattr(item, "to_dict") else dict(item)).get("is_uptrend", False))
    ]

    init_db()
    with open_session() as session:
        rows_written = replace_for_date(session, resolved_date, rows)

    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "candidate_count": len(candidates),
        "rows_written": rows_written,
    }
