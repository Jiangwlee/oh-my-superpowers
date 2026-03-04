"""Tests for post_close_decision_pipeline module.

Covers: stage hysteresis, entry-stage locking, action priority,
        reduce cooldown persistence, and hard position cap.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import ashare_data.post_close_decision_pipeline as pipeline


class TestStageRules(unittest.TestCase):
    """Stage transition and locking rules."""

    def test_determine_stage_with_hysteresis(self) -> None:
        self.assertEqual(pipeline._determine_stage(0.17, None), "stage1")
        self.assertEqual(pipeline._determine_stage(0.24, None), "stage2")
        self.assertEqual(pipeline._determine_stage(0.21, "stage1"), "stage1")
        self.assertEqual(pipeline._determine_stage(0.19, "stage2"), "stage2")

    def test_entry_stage_locked_for_existing_position(self) -> None:
        state = {"000001": {"entry_stage": "stage1"}}
        self.assertEqual(
            pipeline._resolve_entry_stage(code="000001", current_stage="stage2", hold_vol=100, state=state),
            "stage1",
        )
        self.assertEqual(
            pipeline._resolve_entry_stage(code="000002", current_stage="stage2", hold_vol=100, state=state),
            "stage2",
        )


class TestRiskRules(unittest.TestCase):
    """Action priority and risk controls."""

    def test_exit_has_higher_priority_than_reduce(self) -> None:
        action = pipeline._decide_holding_action(
            close_w=9.0,
            ma10w=10.0,
            ma5d_dev=0.12,
            entry_stage="stage1",
            reduce_allowed=True,
            stop_buffer=0.015,
        )
        self.assertEqual(action, "exit")

    def test_hard_position_cap(self) -> None:
        self.assertEqual(pipeline._capped_target_position(0.45, 0.10, 0.50), 0.50)
        self.assertEqual(pipeline._capped_target_position(0.20, 0.10, 0.50), 0.30)


class TestReduceCooldownPersistence(unittest.TestCase):
    """Reduce cooldown must persist to disk across runs."""

    def test_reduce_cooldown_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "post_close_state.json"
            original = pipeline._STATE_FILE
            pipeline._STATE_FILE = state_file
            try:
                state = pipeline._load_state()
                today = date(2026, 3, 3)

                # First trigger writes cooldown timestamp.
                can_reduce = pipeline._can_reduce_today("000001", state, today, cooldown_days=5)
                self.assertTrue(can_reduce)
                pipeline._mark_reduce("000001", state, today)
                pipeline._save_state(state)

                loaded = pipeline._load_state()
                self.assertIn("000001", loaded)
                self.assertEqual(loaded["000001"]["last_reduce_at"], "2026-03-03")

                # Within cooldown window, reduce is blocked.
                self.assertFalse(
                    pipeline._can_reduce_today("000001", loaded, date(2026, 3, 5), cooldown_days=5)
                )
                # After cooldown, reduce is allowed again.
                self.assertTrue(
                    pipeline._can_reduce_today("000001", loaded, date(2026, 3, 10), cooldown_days=5)
                )
            finally:
                pipeline._STATE_FILE = original


class TestJrjPriceNormalization(unittest.TestCase):
    """JRJ kline prices should be normalized to yuan."""

    def test_parse_jrj_bars_normalizes_large_price_units(self) -> None:
        rows = [
            {
                "nTime": 20260303,
                "nOpenPx": 101200,
                "nLastPx": 99700,
                "nHighPx": 102000,
                "nLowPx": 98000,
                "llVolume": 123400,
            }
        ]
        bars = pipeline._parse_jrj_bars(rows)
        self.assertEqual(len(bars), 1)
        self.assertAlmostEqual(bars[0].open, 10.12, places=3)
        self.assertAlmostEqual(bars[0].close, 9.97, places=3)
        self.assertAlmostEqual(bars[0].high, 10.2, places=3)
        self.assertAlmostEqual(bars[0].low, 9.8, places=3)


if __name__ == "__main__":
    unittest.main()
