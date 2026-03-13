"""Theme semantic enrichment boundary.

Purpose: Define the LLM-only enrichment surface for theme-related semantic fields.

Public API:
    enrich_theme_semantics(theme_row, stock_rows, enrich_fn=None) -> tuple[dict, list[dict]]
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


ThemeEnricher = Callable[[dict[str, Any], list[dict[str, Any]]], tuple[dict[str, Any], list[dict[str, Any]]]]

_PROTECTED_THEME_FIELDS = {
    "trade_date",
    "run_id",
    "theme_name",
    "theme_rank",
    "theme_strength",
    "theme_score",
    "core_stock_count",
    "trend_stock_count",
    "core_trend_stock_count",
}
_PROTECTED_STOCK_FIELDS = {
    "trade_date",
    "run_id",
    "theme_name",
    "code",
    "name",
    "role",
    "is_core",
    "rank_in_theme",
    "trend_score",
    "star_rating",
    "emotion_level",
}


def enrich_theme_semantics(
    theme_row: dict[str, Any],
    stock_rows: list[dict[str, Any]],
    *,
    enrich_fn: ThemeEnricher | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply semantic enrichment while protecting deterministic fields."""
    theme_copy = deepcopy(theme_row)
    stock_copies = deepcopy(stock_rows)

    if enrich_fn is None:
        return theme_copy, stock_copies

    original_theme = deepcopy(theme_copy)
    original_stocks = deepcopy(stock_copies)
    enriched_theme, enriched_stocks = enrich_fn(theme_copy, stock_copies)

    for key in _PROTECTED_THEME_FIELDS:
        enriched_theme[key] = original_theme.get(key)

    for idx, row in enumerate(enriched_stocks):
        original = original_stocks[idx]
        for key in _PROTECTED_STOCK_FIELDS:
            row[key] = original.get(key)

    return enriched_theme, enriched_stocks
