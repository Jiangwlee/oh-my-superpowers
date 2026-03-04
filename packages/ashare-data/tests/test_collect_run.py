"""Tests for collect.run() return value structure."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class TestCollectRunReturnType(unittest.TestCase):
    """Verify run() returns a dict with expected keys."""

    @patch("ashare_data.collect.collect")
    @patch("ashare_data.collect.filter_all")
    @patch("ashare_data.collect.run_sentiment_preprocess")
    @patch("ashare_data.collect.ensure_dirs")
    def test_run_returns_dict_on_success(
        self, mock_dirs, mock_sentiment, mock_filter, mock_collect
    ):
        mock_collect.return_value = {
            "ok_count": 5, "error_count": 0, "total_elapsed_sec": 10.0,
            "sources": {},
        }
        mock_filter.return_value = {
            "converted": 5, "skipped": 0, "errors": 0, "total_size_kb": 100.0,
        }
        mock_sentiment.return_value = {"ok": True, "elapsed_sec": 5.0, "news": {}, "social": {}}

        from ashare_data.collect import run

        result = run(date_str="2026-01-01")
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertIn("data_dir", result)
        self.assertIn("collect", result)
        self.assertIn("filter", result)

    @patch("ashare_data.collect.collect")
    @patch("ashare_data.collect.ensure_dirs")
    def test_run_returns_dict_on_failure(self, mock_dirs, mock_collect):
        mock_collect.side_effect = RuntimeError("network error")

        from ashare_data.collect import run

        result = run(date_str="2026-01-01", run_sentiment=False)
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
