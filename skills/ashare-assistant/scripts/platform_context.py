#!/usr/bin/env python3
"""Sync retained platform facts into the skill data directory.

Purpose: Pull daily retained facts from the platform backend and materialize
         them as local JSON context files for `ashare-assistant`.
Input:   trade date plus optional backend base URL and output directory.
Output:  JSON files under `report/` for trend pool, theme pool, and market review.

Public API:
    sync_platform_context(...) -> dict[str, Any]
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.core import shared as shared_core

_DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _backend_base_url(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("ASHARE_PLATFORM_BASE_URL") or _DEFAULT_BASE_URL
    return value.rstrip("/")


def _data_dir_for_date(trade_date: str, explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    return Path.home() / ".ashare-assistant" / "data" / trade_date


def _fetch_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"{base_url}{path}{query}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sync_platform_context(
    *,
    trade_date: str,
    base_url: str | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Fetch retained facts from backend and write local context files."""
    resolved_base_url = _backend_base_url(base_url)
    data_dir = _data_dir_for_date(trade_date, output_dir)
    report_dir = data_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    trend_rows = _fetch_json(resolved_base_url, "/trend-pool/daily", {"trade_date": trade_date})
    theme_rows = _fetch_json(resolved_base_url, "/theme-pool/daily", {"trade_date": trade_date})
    review_row = _fetch_json(resolved_base_url, f"/market-reviews/daily/{trade_date}")

    theme_stocks: dict[str, Any] = {}
    for row in theme_rows:
        theme_name = str(row.get("theme_name", "")).strip()
        if not theme_name:
            continue
        encoded_name = urllib.parse.quote(theme_name, safe="")
        theme_stocks[theme_name] = _fetch_json(
            resolved_base_url,
            f"/theme-pool/daily/{encoded_name}/stocks",
            {"trade_date": trade_date},
        )

    outputs = {
        "platform_trend_pool": report_dir / "platform_trend_pool.json",
        "platform_theme_pool": report_dir / "platform_theme_pool.json",
        "platform_theme_stocks": report_dir / "platform_theme_stocks.json",
        "platform_market_review": report_dir / "platform_market_review.json",
    }
    payloads = {
        "platform_trend_pool": trend_rows,
        "platform_theme_pool": theme_rows,
        "platform_theme_stocks": theme_stocks,
        "platform_market_review": review_row,
    }
    for key, path in outputs.items():
        path.write_text(json.dumps(payloads[key], ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "trade_date": trade_date,
        "base_url": resolved_base_url,
        "data_dir": str(data_dir),
        "written_files": {key: str(path) for key, path in outputs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="同步平台 retained facts 到 skill 本地上下文目录")
    parser.add_argument("--date", default=shared_core.today_cn(), help="目标交易日 YYYY-MM-DD")
    parser.add_argument("--base-url", default="", help="平台后端基础 URL")
    parser.add_argument("--output-dir", default="", help="输出目录，默认 ~/.ashare-assistant/data/{DATE}")
    args = parser.parse_args()

    result = sync_platform_context(
        trade_date=args.date,
        base_url=args.base_url or None,
        output_dir=args.output_dir or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
