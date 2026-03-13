"""Backend runtime configuration.

Purpose: Resolve filesystem locations and deterministic scoring parameters.

Public API:
    Settings -- immutable runtime settings container
    settings -- lazily constructed runtime settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_THEME_POOL_PROFILES: dict[str, dict[str, float | int]] = {
    "default": {
        "min_trend_stock_count": 1,
        "min_core_trend_stock_count": 0,
        "weight_theme_strength": 1.0,
        "weight_trend_stock_count": 2.0,
        "weight_core_trend_stock_count": 3.0,
        "weight_strongest_trend_score": 0.05,
    },
    "mainline_strict": {
        "min_trend_stock_count": 2,
        "min_core_trend_stock_count": 1,
        "weight_theme_strength": 0.8,
        "weight_trend_stock_count": 2.5,
        "weight_core_trend_stock_count": 6.0,
        "weight_strongest_trend_score": 0.03,
    },
}


@dataclass(frozen=True)
class Settings:
    """Resolved backend settings."""

    home_dir: Path
    data_dir: Path
    ephemeral_dir: Path
    retained_dir: Path
    database_path: Path
    theme_pool_profile: str
    theme_pool_min_trend_stock_count: int
    theme_pool_min_core_trend_stock_count: int
    theme_pool_weight_theme_strength: float
    theme_pool_weight_trend_stock_count: float
    theme_pool_weight_core_trend_stock_count: float
    theme_pool_weight_strongest_trend_score: float
    theme_semantic_enrich_enabled: bool
    market_review_semantic_enrich_enabled: bool
    openai_base_url: str | None
    openai_model: str | None
    openai_api_key: str | None


def _default_home_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _theme_pool_profile() -> str:
    profile = os.environ.get("ASHARE_THEME_POOL_PROFILE", "default").strip() or "default"
    if profile not in _THEME_POOL_PROFILES:
        raise ValueError(f"Unsupported ASHARE_THEME_POOL_PROFILE: {profile}")
    return profile


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return float(raw)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _str_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build backend settings and ensure required directories exist."""
    home_dir = Path(os.environ.get("ASHARE_PLATFORM_HOME") or _default_home_dir())
    home_dir.mkdir(parents=True, exist_ok=True)

    data_dir = home_dir / "data"
    ephemeral_dir = data_dir / "ephemeral"
    retained_dir = data_dir / "retained"
    for path in (data_dir, ephemeral_dir, retained_dir):
        path.mkdir(parents=True, exist_ok=True)

    database_path = retained_dir / "ashare_platform.db"
    theme_profile = _theme_pool_profile()
    theme_defaults = _THEME_POOL_PROFILES[theme_profile]
    return Settings(
        home_dir=home_dir,
        data_dir=data_dir,
        ephemeral_dir=ephemeral_dir,
        retained_dir=retained_dir,
        database_path=database_path,
        theme_pool_profile=theme_profile,
        theme_pool_min_trend_stock_count=_int_env(
            "ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT",
            int(theme_defaults["min_trend_stock_count"]),
        ),
        theme_pool_min_core_trend_stock_count=_int_env(
            "ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT",
            int(theme_defaults["min_core_trend_stock_count"]),
        ),
        theme_pool_weight_theme_strength=_float_env(
            "ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH",
            float(theme_defaults["weight_theme_strength"]),
        ),
        theme_pool_weight_trend_stock_count=_float_env(
            "ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT",
            float(theme_defaults["weight_trend_stock_count"]),
        ),
        theme_pool_weight_core_trend_stock_count=_float_env(
            "ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT",
            float(theme_defaults["weight_core_trend_stock_count"]),
        ),
        theme_pool_weight_strongest_trend_score=_float_env(
            "ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE",
            float(theme_defaults["weight_strongest_trend_score"]),
        ),
        theme_semantic_enrich_enabled=_bool_env("ASHARE_THEME_SEMANTIC_ENRICH_ENABLED", False),
        market_review_semantic_enrich_enabled=_bool_env("ASHARE_MARKET_REVIEW_SEMANTIC_ENRICH_ENABLED", False),
        openai_base_url=_str_env("OPENAI_BASE_URL"),
        openai_model=_str_env("OPENAI_MODEL"),
        openai_api_key=_str_env("OPENAI_API_KEY"),
    )


settings = get_settings()
