"""Tests for the red-for-n-days screening pipeline."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestRedForNDays(unittest.TestCase):
    """Red-for-n-days pipeline tests."""

    def test_build_red_for_n_days_filters_for_consecutive_red_bars(self) -> None:
        from app.pipelines.red_for_n_days import build_red_for_n_days

        candidates = [
            {"code": "000001", "sc": "SZ000001", "name": "平安银行", "rank": 1},
            {"code": "000002", "sc": "SZ000002", "name": "万科A", "rank": 2},
            {"code": "000003", "sc": "SZ000003", "name": "国华网安", "rank": 3},
        ]
        kline_map = {
            "000001": [
                {"time": 20260311, "open": 10.0, "close": 10.1},
                {"time": 20260312, "open": 10.2, "close": 10.2},
                {"time": 20260313, "open": 10.3, "close": 10.6},
            ],
            "000002": [
                {"time": 20260311, "open": 20.0, "close": 20.1},
                {"time": 20260312, "open": 20.2, "close": 20.0},
                {"time": 20260313, "open": 20.0, "close": 20.4},
            ],
            "000003": [
                {"time": 20260312, "open": 8.0, "close": 8.1},
                {"time": 20260313, "open": 8.1, "close": 8.2},
            ],
        }

        result = build_red_for_n_days(
            trade_date="2026-03-13",
            days=3,
            top_n=2000,
            fetch_candidates=lambda **_: candidates,
            fetch_daily_kline=lambda code, **_: kline_map[code],
        )

        self.assertEqual(result["trade_date"], "2026-03-13")
        self.assertEqual(result["top_n"], 2000)
        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["insufficient_kline_count"], 1)
        self.assertEqual(result["matches"][0]["code"], "000001")
        self.assertEqual(result["matches"][0]["gain_n_days_pct"], 6.0)
        self.assertEqual(result["matches"][0]["bars"][1]["close"], 10.2)

    def test_build_red_for_n_days_uses_latest_trade_date_when_missing(self) -> None:
        from app.pipelines.red_for_n_days import build_red_for_n_days

        result = build_red_for_n_days(
            days=2,
            fetch_candidates=lambda **_: [],
            fetch_daily_kline=lambda *_args, **_kwargs: [],
            fetch_latest_trade_date=lambda: "20260313",
        )

        self.assertEqual(result["trade_date"], "2026-03-13")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["matched_count"], 0)
