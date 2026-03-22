"""Read-only emotion routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db.session import init_db, open_session
from app.models.market_emotion_daily import MarketEmotionDaily
from app.models.theme_emotion_daily import ThemeEmotionDaily
from app.schemas.api import MarketEmotionDailyResponse, ThemeEmotionDailyResponse

router = APIRouter(tags=["emotion"])


def _to_market_response(row: MarketEmotionDaily) -> MarketEmotionDailyResponse:
    return MarketEmotionDailyResponse(
        trade_date=row.trade_date.isoformat(),
        source=row.source,
        limit_up_count=row.limit_up_count,
        limit_down_count=row.limit_down_count,
        highest_board=row.highest_board,
        limit_up_ladder_count=row.limit_up_ladder_count,
        board_ge_2_count=row.board_ge_2_count,
        board_ge_3_count=row.board_ge_3_count,
        board_ge_4_count=row.board_ge_4_count,
        advance_count=row.advance_count,
        decline_count=row.decline_count,
        flat_count=row.flat_count,
        blowup_rate=row.blowup_rate,
        seal_rate=row.seal_rate,
        promotion_2to3_total=row.promotion_2to3_total,
        promotion_2to3_success=row.promotion_2to3_success,
        promotion_3to4_total=row.promotion_3to4_total,
        promotion_3to4_success=row.promotion_3to4_success,
        market_volume=row.market_volume,
        yesterday_limit_up_return=row.yesterday_limit_up_return,
        theme_count=row.theme_count,
        top_theme_name=row.top_theme_name,
        top_theme_limit_up_num=row.top_theme_limit_up_num,
        highest_board_3d_delta=row.highest_board_3d_delta,
        highest_board_5d_delta=row.highest_board_5d_delta,
        board_ge_3_count_3d_delta=row.board_ge_3_count_3d_delta,
        board_ge_4_count_3d_delta=row.board_ge_4_count_3d_delta,
        limit_up_count_3d_delta=row.limit_up_count_3d_delta,
        limit_down_count_3d_delta=row.limit_down_count_3d_delta,
        top_theme_limit_up_num_3d_delta=row.top_theme_limit_up_num_3d_delta,
        heat_score=row.heat_score,
        risk_score=row.risk_score,
        emotion_score=row.emotion_score,
        cycle_stage_hint=row.cycle_stage_hint,
        evidence_json=row.evidence_json,
    )


def _to_theme_response(row: ThemeEmotionDaily) -> ThemeEmotionDailyResponse:
    return ThemeEmotionDailyResponse(
        trade_date=row.trade_date.isoformat(),
        theme_name=row.theme_name,
        theme_rank=row.theme_rank,
        source=row.source,
        limit_up_num=row.limit_up_num,
        theme_change_pct=row.theme_change_pct,
        sample_stock_count=row.sample_stock_count,
        first_limit_count=row.first_limit_count,
        limit_back_count=row.limit_back_count,
        high_limit_count=row.high_limit_count,
        leader_names_json=row.leader_names_json,
        leader_board_max=row.leader_board_max,
        leader_board_count_ge_2=row.leader_board_count_ge_2,
        leader_continuity_score=row.leader_continuity_score,
        theme_rank_3d_delta=row.theme_rank_3d_delta,
        limit_up_num_3d_delta=row.limit_up_num_3d_delta,
        limit_up_num_5d_delta=row.limit_up_num_5d_delta,
        theme_change_3d_mean=row.theme_change_3d_mean,
        leader_board_max_3d_trend=row.leader_board_max_3d_trend,
        heat_score=row.heat_score,
        risk_score=row.risk_score,
        theme_cycle_hint=row.theme_cycle_hint,
        evidence_json=row.evidence_json,
    )


@router.get("/market-emotion/daily/{trade_date}", response_model=MarketEmotionDailyResponse)
def get_market_emotion_daily(trade_date: str) -> MarketEmotionDailyResponse:
    """Get one daily market emotion row."""
    init_db()
    with open_session() as session:
        row = session.query(MarketEmotionDaily).filter(MarketEmotionDaily.trade_date == trade_date).one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="market emotion not found")
        return _to_market_response(row)


@router.get("/market-emotion/history", response_model=list[MarketEmotionDailyResponse])
def get_market_emotion_history(
    days: int = Query(default=20, ge=1, le=60),
    end_date: str | None = Query(default=None),
) -> list[MarketEmotionDailyResponse]:
    """Get recent market emotion rows."""
    init_db()
    with open_session() as session:
        resolved_end_date = end_date
        if resolved_end_date is None:
            latest_row = (
                session.query(MarketEmotionDaily)
                .order_by(MarketEmotionDaily.trade_date.desc())
                .first()
            )
            if latest_row is None:
                return []
            resolved_end_date = latest_row.trade_date.isoformat()
        rows = (
            session.query(MarketEmotionDaily)
            .filter(MarketEmotionDaily.trade_date <= resolved_end_date)
            .order_by(MarketEmotionDaily.trade_date.desc())
            .limit(days)
            .all()
        )
        return [_to_market_response(row) for row in reversed(rows)]


@router.get("/theme-emotion/daily", response_model=list[ThemeEmotionDailyResponse])
def get_theme_emotion_daily(
    trade_date: str = Query(...),
    cycle_hint: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="theme_rank"),
) -> list[ThemeEmotionDailyResponse]:
    """Get daily theme emotion rows."""
    init_db()
    with open_session() as session:
        query = session.query(ThemeEmotionDaily).filter(ThemeEmotionDaily.trade_date == trade_date)
        if cycle_hint:
            query = query.filter(ThemeEmotionDaily.theme_cycle_hint == cycle_hint)
        if sort == "-heat_score":
            query = query.order_by(ThemeEmotionDaily.heat_score.desc(), ThemeEmotionDaily.theme_rank.asc())
        elif sort == "-limit_up_num":
            query = query.order_by(ThemeEmotionDaily.limit_up_num.desc(), ThemeEmotionDaily.theme_rank.asc())
        else:
            query = query.order_by(ThemeEmotionDaily.theme_rank.asc())
        rows = query.limit(limit).all()
        return [_to_theme_response(row) for row in rows]


@router.get("/theme-emotion/themes/{theme_name}/history", response_model=list[ThemeEmotionDailyResponse])
def get_theme_emotion_history(
    theme_name: str,
    days: int = Query(default=20, ge=1, le=60),
) -> list[ThemeEmotionDailyResponse]:
    """Get recent theme emotion rows for one theme."""
    init_db()
    with open_session() as session:
        rows = (
            session.query(ThemeEmotionDaily)
            .filter(ThemeEmotionDaily.theme_name == theme_name)
            .order_by(ThemeEmotionDaily.trade_date.desc())
            .limit(days)
            .all()
        )
        return [_to_theme_response(row) for row in reversed(rows)]
