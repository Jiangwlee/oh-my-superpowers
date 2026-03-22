"""Tests for collect-all task orchestration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestCollectAll(unittest.TestCase):
    """collect-all task tests."""

    def test_collect_all_runs_retained_steps_for_one_trade_date(self) -> None:
        from app.tasks.collect_all import run

        with patch("app.tasks.collect_all.run_build_emotion_facts", side_effect=lambda trade_date: {"pipeline": "emotion", "trade_date": trade_date}) as mocked_emotion:
            with patch("app.tasks.collect_all.run_build_trend_pool", side_effect=lambda trade_date, max_rank: {"pipeline": "trend", "trade_date": trade_date, "max_rank": max_rank}) as mocked_trend:
                with patch("app.tasks.collect_all.run_build_theme_pool", side_effect=lambda trade_date: {"pipeline": "theme", "trade_date": trade_date}) as mocked_theme:
                    with patch("app.tasks.collect_all.run_build_market_review", side_effect=lambda trade_date: {"pipeline": "review", "trade_date": trade_date}) as mocked_review:
                        result = run(trade_date="2026-03-13", trend_max_rank=500)

        mocked_emotion.assert_called_once_with(trade_date="2026-03-13")
        mocked_trend.assert_called_once_with(trade_date="2026-03-13", max_rank=500)
        mocked_theme.assert_called_once_with(trade_date="2026-03-13")
        mocked_review.assert_called_once_with(trade_date="2026-03-13")
        self.assertEqual(result["trade_date"], "2026-03-13")
        self.assertEqual(result["run"]["build_trend_pool"]["max_rank"], 500)

    def test_collect_all_optionally_runs_ephemeral_collection(self) -> None:
        from app.tasks.collect_all import run

        with patch("app.tasks.collect_all.run_collect_ephemeral", return_value={"pipeline": "ephemeral"}) as mocked_collect:
            with patch("app.tasks.collect_all.run_build_emotion_facts", return_value={"pipeline": "emotion"}):
                with patch("app.tasks.collect_all.run_build_trend_pool", return_value={"pipeline": "trend"}):
                    with patch("app.tasks.collect_all.run_build_theme_pool", return_value={"pipeline": "theme"}):
                        with patch("app.tasks.collect_all.run_build_market_review", return_value={"pipeline": "review"}):
                            result = run(
                                trade_date="2026-03-13",
                                with_ephemeral=True,
                                news_count=50,
                                taoguba_count=40,
                                scan_trends=False,
                                popularity_max=800,
                            )

        mocked_collect.assert_called_once_with(
            trade_date="2026-03-13",
            news_count=50,
            taoguba_count=40,
            scan_trends=False,
            popularity_max=800,
        )
        self.assertIn("collect_ephemeral", result["run"])


class TestInitData(unittest.TestCase):
    """init-data task tests."""

    def test_init_data_backfills_trade_window_without_analysis_steps(self) -> None:
        from app.tasks.init_data import run

        with patch("app.tasks.init_data.resolve_trade_dates", return_value=["2026-03-12", "2026-03-13"]) as mocked_dates:
            with patch(
                "app.tasks.init_data.run_build_emotion_facts",
                side_effect=lambda trade_date: {"pipeline": "emotion", "trade_date": trade_date},
            ) as mocked_emotion:
                result = run(trade_date="2026-03-13", days=2)

        mocked_dates.assert_called_once_with(end_date="2026-03-13", days=2)
        self.assertEqual(mocked_emotion.call_count, 2)
        self.assertEqual(result["trade_dates"], ["2026-03-12", "2026-03-13"])
        self.assertEqual(result["runs"][0]["build_emotion_facts"]["pipeline"], "emotion")
