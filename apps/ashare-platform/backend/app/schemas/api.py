"""API response schemas for backend routes.

Purpose: Define stable HTTP response payloads for read-only platform APIs.
"""

from __future__ import annotations

from pydantic import BaseModel


class RunResponse(BaseModel):
    run_id: str
    trade_date: str
    pipeline_name: str
    status: str
    degraded: bool


class TrendPoolDailyResponse(BaseModel):
    trade_date: str
    code: str
    name: str
    rank: int
    score_total: float
    star_rating: int
    emotion_level: int
    trade_signal: str
    is_uptrend: bool


class ThemePoolDailyResponse(BaseModel):
    trade_date: str
    theme_name: str
    theme_rank: int
    theme_strength: float | None = None
    theme_stage: str | None = None
    market_attitude: str | None = None
    core_stock_count: int
    summary: str | None = None


class ThemeStockDailyResponse(BaseModel):
    trade_date: str
    theme_name: str
    code: str
    name: str
    role: str | None = None
    is_core: bool
    rank_in_theme: int
    trend_score: float | None = None
    star_rating: int | None = None
    emotion_level: int | None = None
    comment: str | None = None


class MarketReviewDailyResponse(BaseModel):
    trade_date: str
    run_id: str
    regime: str | None = None
    position_guidance: str | None = None
    main_themes: list[str] = []
    emerging_themes: list[str] = []
    fading_themes: list[str] = []
    summary: str | None = None
    report_markdown: str
