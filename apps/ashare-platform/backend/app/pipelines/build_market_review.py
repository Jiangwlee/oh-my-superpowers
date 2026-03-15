"""Market review build pipeline.

Purpose: Produce one retained daily market review from trend/theme daily facts.

Public API:
    build_market_review(...) -> dict
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from sqlalchemy import desc

from app.core.config import get_settings
from app.core.runtime import build_run_id
from app.db.session import init_db, open_session
from app.models.market_emotion_daily import MarketEmotionDaily
from app.models.theme_pool_daily import ThemePoolDaily
from app.models.trend_pool_daily import TrendPoolDaily
from app.repositories.market_review_repository import replace_for_date
from app.services.market_review_semantic_enricher import create_market_review_semantic_enricher


def _default_markdown_builder(
    *,
    trade_date: str,
    main_themes: list[str],
    strong_trend_codes: list[str],
) -> str:
    lines = [
        f"# 市场复盘 - {trade_date}",
        "",
        "## 主线题材",
        "",
    ]
    if main_themes:
        for theme in main_themes:
            lines.append(f"- {theme}")
    else:
        lines.append("- 待确认")
    lines.extend(["", "## 趋势观察", ""])
    if strong_trend_codes:
        for code in strong_trend_codes:
            lines.append(f"- {code}")
    else:
        lines.append("- 待确认")
    return "\n".join(lines)


def build_market_review(
    *,
    trade_date: str,
    markdown_builder: Callable[..., str] = _default_markdown_builder,
    semantic_enricher: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build and persist one market review row."""
    resolved_date = date.fromisoformat(trade_date)
    run_id = build_run_id(trade_date, "build-market-review")
    settings = get_settings()
    effective_enricher = semantic_enricher
    if effective_enricher is None and settings.market_review_semantic_enrich_enabled:
        try:
            effective_enricher = create_market_review_semantic_enricher()
        except ValueError:
            effective_enricher = None

    init_db()
    with open_session() as session:
        main_theme_rows = (
            session.query(ThemePoolDaily)
            .filter(ThemePoolDaily.trade_date == resolved_date)
            .order_by(ThemePoolDaily.theme_rank)
            .limit(3)
            .all()
        )
        market_emotion_row = (
            session.query(MarketEmotionDaily)
            .filter(MarketEmotionDaily.trade_date == resolved_date)
            .one_or_none()
        )
        trend_rows = (
            session.query(TrendPoolDaily)
            .filter(TrendPoolDaily.trade_date == resolved_date)
            .order_by(desc(TrendPoolDaily.star_rating), desc(TrendPoolDaily.score_total))
            .limit(5)
            .all()
        )

        main_themes = [row.theme_name for row in main_theme_rows]
        strong_trend_codes = [row.code for row in trend_rows]
        regime = "strong" if len(main_themes) >= 2 else "neutral"
        position_guidance = "60-80%" if regime == "strong" else "30-50%"
        report_markdown = markdown_builder(
            trade_date=trade_date,
            main_themes=main_themes,
            strong_trend_codes=strong_trend_codes,
        )
        row = {
            "trade_date": resolved_date,
            "run_id": run_id,
            "regime": regime,
            "position_guidance": position_guidance,
            "main_themes_json": main_themes,
            "emerging_themes_json": [],
            "fading_themes_json": [],
            "market_emotion_json": (
                {
                    "limit_up_count": market_emotion_row.limit_up_count,
                    "limit_down_count": market_emotion_row.limit_down_count,
                    "blowup_rate": market_emotion_row.blowup_rate,
                    "highest_board": market_emotion_row.highest_board,
                    "cycle_stage_hint": market_emotion_row.cycle_stage_hint,
                    "risk_score": market_emotion_row.risk_score,
                    "emotion_score": market_emotion_row.emotion_score,
                }
                if market_emotion_row is not None
                else None
            ),
            "themes_json": [
                {
                    "theme_name": theme.theme_name,
                    "theme_rank": theme.theme_rank,
                    "theme_stage": theme.theme_stage,
                    "market_attitude": theme.market_attitude,
                    "summary": theme.summary,
                }
                for theme in main_theme_rows
            ],
            "trend_codes_json": strong_trend_codes,
            "summary": None,
            "report_markdown": report_markdown,
            "report_version": "v1",
        }
        if effective_enricher is not None:
            enriched = effective_enricher(dict(row))
            row["summary"] = enriched.get("summary")
            row["report_markdown"] = str(enriched.get("report_markdown") or row["report_markdown"])
        row.pop("market_emotion_json", None)
        row.pop("themes_json", None)
        row.pop("trend_codes_json", None)
        stored = replace_for_date(session, resolved_date, row)

    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "stored": stored,
    }
