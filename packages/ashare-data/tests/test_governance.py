"""Tests for governance helpers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ashare_data.core import governance


class TestGovernance(unittest.TestCase):
    """Retention and quality gate behavior."""

    def test_apply_retention_policy_prunes_old_data_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            data_dir = home / "data"
            signals_dir = home / "signals"
            memory_dir = home / "memory"
            data_dir.mkdir(parents=True, exist_ok=True)
            signals_dir.mkdir(parents=True, exist_ok=True)
            memory_dir.mkdir(parents=True, exist_ok=True)

            (data_dir / "2020-01-01" / "raw").mkdir(parents=True, exist_ok=True)
            (data_dir / "2020-01-01" / "raw" / "x.json").write_text("{}", encoding="utf-8")
            (data_dir / "2099-01-01" / "raw").mkdir(parents=True, exist_ok=True)
            (data_dir / "2099-01-01" / "raw" / "x.json").write_text("{}", encoding="utf-8")

            old_signal = signals_dir / "old_signal.json"
            old_signal.write_text("{}", encoding="utf-8")
            os.utime(old_signal, (0, 0))
            keep_signal = signals_dir / "watchlist_signals.json"
            keep_signal.write_text("{}", encoding="utf-8")

            decision_log = memory_dir / "decision_log.jsonl"
            decision_log.write_text(
                json.dumps({"as_of_date": "2020-01-01", "k": 1}, ensure_ascii=False) + "\n"
                + json.dumps({"as_of_date": "2099-01-01", "k": 2}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            with patch.object(governance, "ASHARE_HOME", home), patch.object(
                governance, "DATA_DIR", data_dir
            ), patch.object(governance, "DECISION_LOG", decision_log):
                result = governance.apply_retention_policy(data_days=30, signals_days=30, decision_log_days=365)

            self.assertIn("2020-01-01", result["removed_data_dirs"])
            self.assertNotIn("2099-01-01", result["removed_data_dirs"])
            self.assertIn("old_signal.json", result["removed_signal_files"])
            self.assertTrue(keep_signal.exists())
            self.assertEqual(result["decision_log_pruned"], 1)
            lines = decision_log.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)

    def test_evaluate_degraded_detects_errors_and_empty_sources(self) -> None:
        sources = {
            "trade_date": {"status": "ok", "dq": {"is_empty": False}},
            "news_headline": {"status": "ok", "dq": {"is_empty": True}},
            "funding": {"status": "error", "dq": {"is_empty": None}},
            "trend_scan": {"status": "ok", "dq": {"is_empty": False}},
        }
        degraded, reasons = governance.evaluate_degraded(sources, error_count=1, filter_errors=0)
        self.assertTrue(degraded)
        self.assertIn("collect_error_count=1", reasons)
        self.assertIn("source_empty=news_headline", reasons)
        self.assertIn("source_status_funding=error", reasons)


if __name__ == "__main__":
    unittest.main()
