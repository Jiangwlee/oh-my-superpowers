"""Trend pool daily fact model.

Purpose: Persist one daily trend-pool fact row per stock and trade date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TrendPoolDaily(Base):
    """Daily trend pool fact."""

    __tablename__ = "trend_pool_daily"
    __table_args__ = (UniqueConstraint("trade_date", "code", name="uq_trend_pool_daily_date_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(64))
    rank: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(64), default="")
    score_total: Mapped[float] = mapped_column(Float, default=0.0)
    star_rating: Mapped[int] = mapped_column(Integer, default=0)
    emotion_level: Mapped[int] = mapped_column(Integer, default=0)
    emotion_label: Mapped[str] = mapped_column(String(32), default="")
    trade_signal: Mapped[str] = mapped_column(String(32), default="")
    is_uptrend: Mapped[bool] = mapped_column(Boolean, default=False)
    gain_30_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    gain_60_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    holding_experience: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
