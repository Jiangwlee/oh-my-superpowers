"""Market emotion daily fact model.

Purpose: Persist one market-level emotion fact row per trade date.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import DATE, JSON, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    """Return timezone-aware UTC time for row creation."""
    return datetime.now(timezone.utc)


class MarketEmotionDaily(Base):
    """Daily market emotion fact."""

    __tablename__ = "market_emotion_daily"
    __table_args__ = (UniqueConstraint("trade_date", name="uq_market_emotion_daily_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(DATE, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(32), default="ths")
    limit_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    highest_board: Mapped[int] = mapped_column(Integer, default=0)
    limit_up_ladder_count: Mapped[int] = mapped_column(Integer, default=0)
    board_ge_2_count: Mapped[int] = mapped_column(Integer, default=0)
    board_ge_3_count: Mapped[int] = mapped_column(Integer, default=0)
    board_ge_4_count: Mapped[int] = mapped_column(Integer, default=0)
    advance_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decline_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flat_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theme_count: Mapped[int] = mapped_column(Integer, default=0)
    top_theme_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    top_theme_limit_up_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blowup_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    seal_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    promotion_2to3_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promotion_2to3_success: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promotion_3to4_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promotion_3to4_success: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    yesterday_limit_up_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_board_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    highest_board_5d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    board_ge_3_count_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    board_ge_4_count_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_up_count_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down_count_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_theme_limit_up_num_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    emotion_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cycle_stage_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
