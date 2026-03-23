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
    theme_score: float | None = None
    theme_stage: str | None = None
    market_attitude: str | None = None
    core_stock_count: int
    trend_stock_count: int
    core_trend_stock_count: int
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
    continue_num: int | None = None
    change_rate: float | None = None
    reason_type: str | None = None
    change_tag: str | None = None


class KlineDailyResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: float | None = None


class LatestTradeDateResponse(BaseModel):
    trade_date: str


class RecentTradeDatesResponse(BaseModel):
    days: int
    trade_dates: list[str]


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


class MarketEmotionDailyResponse(BaseModel):
    trade_date: str
    source: str
    limit_up_count: int | None = None
    limit_down_count: int | None = None
    highest_board: int
    limit_up_ladder_count: int
    board_ge_2_count: int
    board_ge_3_count: int
    board_ge_4_count: int
    advance_count: int | None = None
    decline_count: int | None = None
    flat_count: int | None = None
    blowup_rate: float | None = None
    seal_rate: float | None = None
    promotion_2to3_total: int | None = None
    promotion_2to3_success: int | None = None
    promotion_3to4_total: int | None = None
    promotion_3to4_success: int | None = None
    market_volume: float | None = None
    yesterday_limit_up_return: float | None = None
    theme_count: int
    top_theme_name: str | None = None
    top_theme_limit_up_num: int | None = None
    highest_board_3d_delta: int | None = None
    highest_board_5d_delta: int | None = None
    board_ge_3_count_3d_delta: int | None = None
    board_ge_4_count_3d_delta: int | None = None
    limit_up_count_3d_delta: int | None = None
    limit_down_count_3d_delta: int | None = None
    top_theme_limit_up_num_3d_delta: int | None = None
    heat_score: float | None = None
    risk_score: float | None = None
    emotion_score: float | None = None
    cycle_stage_hint: str | None = None
    evidence_json: dict | list | None = None


class ThemeEmotionDailyResponse(BaseModel):
    trade_date: str
    theme_name: str
    theme_rank: int
    source: str
    limit_up_num: int
    theme_change_pct: float | None = None
    sample_stock_count: int
    first_limit_count: int
    limit_back_count: int
    high_limit_count: int
    leader_names_json: list[str] | dict | None = None
    leader_board_max: int
    leader_board_count_ge_2: int
    leader_continuity_score: float | None = None
    theme_rank_3d_delta: int | None = None
    limit_up_num_3d_delta: int | None = None
    limit_up_num_5d_delta: int | None = None
    theme_change_3d_mean: float | None = None
    leader_board_max_3d_trend: int | None = None
    heat_score: float | None = None
    risk_score: float | None = None
    theme_cycle_hint: str | None = None
    evidence_json: dict | list | None = None
