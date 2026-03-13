"""Theme emotion daily fact model.

Purpose: Persist one theme-level emotion fact row per theme and trade date.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import DATE, JSON, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    """Return timezone-aware UTC time for row creation."""
    return datetime.now(timezone.utc)


class ThemeEmotionDaily(Base):
    """Daily theme emotion fact."""

    __tablename__ = "theme_emotion_daily"
    __table_args__ = (UniqueConstraint("trade_date", "theme_name", name="uq_theme_emotion_daily_date_theme"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(DATE, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    theme_name: Mapped[str] = mapped_column(String(128), index=True)
    theme_rank: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32), default="ths_block_top")
    limit_up_num: Mapped[int] = mapped_column(Integer, default=0)
    theme_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_stock_count: Mapped[int] = mapped_column(Integer, default=0)
    leader_names_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    leader_board_max: Mapped[int] = mapped_column(Integer, default=0)
    leader_board_count_ge_2: Mapped[int] = mapped_column(Integer, default=0)
    first_limit_count: Mapped[int] = mapped_column(Integer, default=0)
    limit_back_count: Mapped[int] = mapped_column(Integer, default=0)
    high_limit_count: Mapped[int] = mapped_column(Integer, default=0)
    theme_rank_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_up_num_3d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_up_num_5d_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theme_change_3d_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    leader_board_max_3d_trend: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leader_continuity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    theme_cycle_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
