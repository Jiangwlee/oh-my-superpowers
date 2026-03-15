"""Theme pool build pipeline.

Purpose: Produce retained daily theme facts from THS block-top data and trend facts.

Public API:
    build_theme_pool(...) -> dict
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from ashare_data.fetchers.trend_scanner import fetch_ths_snapshot

from app.core.config import get_settings
from app.core.runtime import build_run_id
from app.db.session import init_db, open_session
from app.models.market_emotion_daily import MarketEmotionDaily
from app.models.theme_emotion_daily import ThemeEmotionDaily
from app.models.trend_pool_daily import TrendPoolDaily
from app.pipelines.enrich_theme_semantics import ThemeEnricher, enrich_theme_semantics
from app.repositories.theme_pool_repository import replace_for_date
from app.services.theme_semantic_enricher import create_theme_semantic_enricher


def _normalize_trade_date(trade_date: str) -> tuple[date, str]:
    resolved = date.fromisoformat(trade_date)
    ths_date = resolved.strftime("%Y%m%d")
    return resolved, ths_date


def _load_trend_map(session: Any, resolved_date: date) -> dict[str, TrendPoolDaily]:
    rows = session.query(TrendPoolDaily).filter(TrendPoolDaily.trade_date == resolved_date).all()
    return {row.code: row for row in rows}


def _load_market_emotion(session: Any, resolved_date: date) -> dict[str, Any] | None:
    row = (
        session.query(MarketEmotionDaily)
        .filter(MarketEmotionDaily.trade_date == resolved_date)
        .one_or_none()
    )
    if row is None:
        return None
    return {
        "limit_up_count": row.limit_up_count,
        "limit_down_count": row.limit_down_count,
        "blowup_rate": row.blowup_rate,
        "highest_board": row.highest_board,
        "board_ge_3_count": row.board_ge_3_count,
        "board_ge_4_count": row.board_ge_4_count,
        "cycle_stage_hint": row.cycle_stage_hint,
        "risk_score": row.risk_score,
        "emotion_score": row.emotion_score,
    }


def _load_theme_emotion_map(session: Any, resolved_date: date) -> dict[str, dict[str, Any]]:
    rows = session.query(ThemeEmotionDaily).filter(ThemeEmotionDaily.trade_date == resolved_date).all()
    return {
        row.theme_name: {
            "limit_up_num": row.limit_up_num,
            "theme_change_pct": row.theme_change_pct,
            "leader_board_max": row.leader_board_max,
            "leader_board_count_ge_2": row.leader_board_count_ge_2,
            "limit_up_num_3d_delta": row.limit_up_num_3d_delta,
            "limit_up_num_5d_delta": row.limit_up_num_5d_delta,
            "theme_change_3d_mean": row.theme_change_3d_mean,
            "leader_continuity_score": row.leader_continuity_score,
            "heat_score": row.heat_score,
            "risk_score": row.risk_score,
            "theme_cycle_hint": row.theme_cycle_hint,
        }
        for row in rows
    }


def _should_keep_theme_stock(stock_idx: int, trend_row: TrendPoolDaily | None) -> bool:
    return stock_idx <= 3 or trend_row is not None


def _theme_stage(limit_up_num: int, change: float | None) -> str:
    if limit_up_num >= 6:
        return "middle"
    if limit_up_num >= 3:
        return "early"
    if change is not None and change < 0:
        return "late"
    return "unknown"


def _theme_strength(limit_up_num: int, change: float | None) -> float:
    base = float(limit_up_num)
    if change is not None:
        base += max(change, 0.0)
    return round(base, 2)


def _theme_score(
    *,
    theme_strength: float,
    trend_stock_count: int,
    core_trend_stock_count: int,
    strongest_trend_score: float,
    weight_theme_strength: float,
    weight_trend_stock_count: float,
    weight_core_trend_stock_count: float,
    weight_strongest_trend_score: float,
) -> float:
    return round(
        theme_strength * weight_theme_strength
        + trend_stock_count * weight_trend_stock_count
        + core_trend_stock_count * weight_core_trend_stock_count
        + strongest_trend_score * weight_strongest_trend_score,
        2,
    )


def build_theme_pool(
    *,
    trade_date: str,
    snapshot_fetcher: Callable[..., dict[str, Any]] = fetch_ths_snapshot,
    semantic_enricher: ThemeEnricher | None = None,
) -> dict[str, Any]:
    """Build and persist one day of theme pool facts."""
    resolved_date, ths_date = _normalize_trade_date(trade_date)
    run_id = build_run_id(trade_date, "build-theme-pool")
    settings = get_settings()
    effective_enricher = semantic_enricher
    if effective_enricher is None and settings.theme_semantic_enrich_enabled:
        try:
            effective_enricher = create_theme_semantic_enricher()
        except ValueError:
            effective_enricher = None
    snapshot = snapshot_fetcher(end_date=ths_date)
    block_top = snapshot.get("block_top") or []

    init_db()
    with open_session() as session:
        trend_map = _load_trend_map(session, resolved_date)
        market_emotion = _load_market_emotion(session, resolved_date)
        theme_emotion_map = _load_theme_emotion_map(session, resolved_date)

        theme_rows: list[dict[str, Any]] = []
        stock_rows: list[dict[str, Any]] = []
        for idx, theme in enumerate(block_top, start=1):
            theme_name = str(theme.get("name", "")).strip()
            if not theme_name:
                continue
            limit_up_num = int(theme.get("limit_up_num", 0) or 0)
            change = theme.get("change")
            change_float = float(change) if change is not None else None
            stocks = theme.get("stock_list") or []

            theme_stock_rows: list[dict[str, Any]] = []
            trend_stock_count = 0
            core_trend_stock_count = 0
            strongest_trend_score = 0.0
            for stock_idx, stock in enumerate(stocks, start=1):
                code = str(stock.get("code", "")).strip()
                if not code:
                    continue
                trend_row = trend_map.get(code)
                if trend_row is not None:
                    trend_stock_count += 1
                    if stock_idx <= 3:
                        core_trend_stock_count += 1
                    strongest_trend_score = max(strongest_trend_score, float(trend_row.score_total or 0.0))
                if not _should_keep_theme_stock(stock_idx, trend_row):
                    continue
                theme_stock_rows.append(
                    {
                        "trade_date": resolved_date,
                        "run_id": run_id,
                        "theme_name": theme_name,
                        "code": code,
                        "name": str(stock.get("name", "")).strip() or code,
                        "role": "leader" if stock_idx == 1 else ("core" if stock_idx <= 3 else "follower"),
                        "is_core": stock_idx <= 3,
                        "rank_in_theme": stock_idx,
                        "trend_score": trend_row.score_total if trend_row is not None else None,
                        "star_rating": trend_row.star_rating if trend_row is not None else None,
                        "emotion_level": trend_row.emotion_level if trend_row is not None else None,
                        "comment": None,
                        "evidence_json": {
                            "continue_num": stock.get("continue_num"),
                            "change_rate": stock.get("change_rate"),
                            "reason_type": stock.get("reason_type"),
                            "change_tag": stock.get("change_tag"),
                        },
                    }
                )

            if trend_stock_count < settings.theme_pool_min_trend_stock_count:
                continue
            if core_trend_stock_count < settings.theme_pool_min_core_trend_stock_count:
                continue

            theme_strength = _theme_strength(limit_up_num, change_float)

            theme_row = {
                "trade_date": resolved_date,
                "run_id": run_id,
                "theme_name": theme_name,
                "theme_rank": idx,
                "theme_strength": theme_strength,
                "theme_score": _theme_score(
                    theme_strength=theme_strength,
                    trend_stock_count=trend_stock_count,
                    core_trend_stock_count=core_trend_stock_count,
                    strongest_trend_score=strongest_trend_score,
                    weight_theme_strength=settings.theme_pool_weight_theme_strength,
                    weight_trend_stock_count=settings.theme_pool_weight_trend_stock_count,
                    weight_core_trend_stock_count=settings.theme_pool_weight_core_trend_stock_count,
                    weight_strongest_trend_score=settings.theme_pool_weight_strongest_trend_score,
                ),
                "theme_stage": _theme_stage(limit_up_num, change_float),
                "market_attitude": None,
                "core_stock_count": sum(1 for row in theme_stock_rows if row["is_core"]),
                "trend_stock_count": trend_stock_count,
                "core_trend_stock_count": core_trend_stock_count,
                "summary": None,
                "market_emotion_json": market_emotion,
                "theme_emotion_json": theme_emotion_map.get(theme_name),
                "evidence_json": {
                    "limit_up_num": limit_up_num,
                    "change": change_float,
                    "trend_stock_count": trend_stock_count,
                    "core_trend_stock_count": core_trend_stock_count,
                    "strongest_trend_score": strongest_trend_score,
                },
                "tags_json": {
                    "source": "ths_block_top",
                    "source_rank": idx,
                },
            }

            enriched_theme_row, enriched_stock_rows = enrich_theme_semantics(
                theme_row,
                theme_stock_rows,
                enrich_fn=effective_enricher,
            )
            enriched_theme_row.pop("market_emotion_json", None)
            enriched_theme_row.pop("theme_emotion_json", None)
            theme_rows.append(enriched_theme_row)
            stock_rows.extend(enriched_stock_rows)

        theme_rows.sort(
            key=lambda row: (
                -float(row.get("theme_score", 0.0) or 0.0),
                -int(row.get("trend_stock_count", 0) or 0),
                -int(row.get("core_trend_stock_count", 0) or 0),
                -float(row.get("theme_strength", 0.0) or 0.0),
                int(((row.get("tags_json") or {}).get("source_rank", 0)) or 0),
            )
        )
        for rank, row in enumerate(theme_rows, start=1):
            row["theme_rank"] = rank

        themes_written, stocks_written = replace_for_date(session, resolved_date, theme_rows, stock_rows)

    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "themes_written": themes_written,
        "stocks_written": stocks_written,
    }
