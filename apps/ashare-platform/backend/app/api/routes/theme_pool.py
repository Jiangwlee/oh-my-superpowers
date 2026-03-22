"""Read-only theme pool routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.session import init_db, open_session
from app.models.theme_pool_daily import ThemePoolDaily
from app.models.theme_stock_daily import ThemeStockDaily
from app.schemas.api import ThemePoolDailyResponse, ThemeStockDailyResponse

router = APIRouter(prefix="/theme-pool", tags=["theme-pool"])


def _to_theme_stock_response(row: ThemeStockDaily) -> ThemeStockDailyResponse:
    evidence = row.evidence_json if isinstance(row.evidence_json, dict) else {}
    continue_num = evidence.get("continue_num")
    return ThemeStockDailyResponse(
        trade_date=row.trade_date.isoformat(),
        theme_name=row.theme_name,
        code=row.code,
        name=row.name,
        role=row.role,
        is_core=row.is_core,
        rank_in_theme=row.rank_in_theme,
        trend_score=row.trend_score,
        star_rating=row.star_rating,
        emotion_level=row.emotion_level,
        comment=row.comment,
        continue_num=int(continue_num) if continue_num is not None else None,
        change_rate=float(evidence["change_rate"]) if evidence.get("change_rate") is not None else None,
        reason_type=str(evidence["reason_type"]) if evidence.get("reason_type") is not None else None,
        change_tag=str(evidence["change_tag"]) if evidence.get("change_tag") is not None else None,
    )


@router.get("/daily", response_model=list[ThemePoolDailyResponse])
def get_theme_pool_daily(
    trade_date: str = Query(...),
    stage: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    sort: str = Query(default="theme_rank"),
) -> list[ThemePoolDailyResponse]:
    """Get daily theme pool facts."""
    init_db()
    with open_session() as session:
        query = session.query(ThemePoolDaily).filter(ThemePoolDaily.trade_date == trade_date)
        if stage:
            query = query.filter(ThemePoolDaily.theme_stage == stage)
        if sort == "-theme_score":
            query = query.order_by(ThemePoolDaily.theme_score.desc())
        elif sort == "-theme_strength":
            query = query.order_by(ThemePoolDaily.theme_strength.desc())
        else:
            query = query.order_by(ThemePoolDaily.theme_rank.asc())
        rows = query.limit(limit).all()
        return [
            ThemePoolDailyResponse(
                trade_date=row.trade_date.isoformat(),
                theme_name=row.theme_name,
                theme_rank=row.theme_rank,
                theme_strength=row.theme_strength,
                theme_score=row.theme_score,
                theme_stage=row.theme_stage,
                market_attitude=row.market_attitude,
                core_stock_count=row.core_stock_count,
                trend_stock_count=row.trend_stock_count,
                core_trend_stock_count=row.core_trend_stock_count,
                summary=row.summary,
            )
            for row in rows
        ]


@router.get("/daily/{theme_name}/stocks", response_model=list[ThemeStockDailyResponse])
def get_theme_daily_stocks(
    theme_name: str,
    trade_date: str = Query(...),
) -> list[ThemeStockDailyResponse]:
    """Get theme-stock daily facts for one theme and trade date."""
    init_db()
    with open_session() as session:
        rows = (
            session.query(ThemeStockDaily)
            .filter(ThemeStockDaily.trade_date == trade_date, ThemeStockDaily.theme_name == theme_name)
            .order_by(ThemeStockDaily.rank_in_theme.asc())
            .all()
        )
        return [_to_theme_stock_response(row) for row in rows]


@router.get("/themes/{theme_name}/history", response_model=list[ThemePoolDailyResponse])
def get_theme_history(
    theme_name: str,
    days: int = Query(default=20, ge=1, le=365),
) -> list[ThemePoolDailyResponse]:
    """Get recent daily theme facts for one theme."""
    init_db()
    with open_session() as session:
        rows = (
            session.query(ThemePoolDaily)
            .filter(ThemePoolDaily.theme_name == theme_name)
            .order_by(ThemePoolDaily.trade_date.desc())
            .limit(days)
            .all()
        )
        return [
            ThemePoolDailyResponse(
                trade_date=row.trade_date.isoformat(),
                theme_name=row.theme_name,
                theme_rank=row.theme_rank,
                theme_strength=row.theme_strength,
                theme_score=row.theme_score,
                theme_stage=row.theme_stage,
                market_attitude=row.market_attitude,
                core_stock_count=row.core_stock_count,
                trend_stock_count=row.trend_stock_count,
                core_trend_stock_count=row.core_trend_stock_count,
                summary=row.summary,
            )
            for row in rows
        ]
