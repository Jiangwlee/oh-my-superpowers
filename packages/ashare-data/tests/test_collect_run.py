"""Tests for collect.run() after LLM removal."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch


class TestCollectRunReturnType(unittest.TestCase):
    """Verify run() returns a dict with expected keys (no sentiment)."""

    @patch("ashare_data.collect.collect")
    @patch("ashare_data.collect.filter_all")
    @patch("ashare_data.collect.ensure_dirs")
    def test_run_returns_dict_on_success(
        self, mock_dirs, mock_filter, mock_collect
    ):
        mock_collect.return_value = {
            "ok_count": 5, "error_count": 0, "total_elapsed_sec": 10.0,
            "sources": {},
        }
        mock_filter.return_value = {
            "converted": 5, "skipped": 0, "errors": 0, "total_size_kb": 100.0,
        }

        from ashare_data.collect import run

        result = run(date_str="2026-01-01")
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertIn("data_dir", result)
        self.assertIn("collect", result)
        self.assertIn("filter", result)
        self.assertNotIn("sentiment", result)

    @patch("ashare_data.collect.collect")
    @patch("ashare_data.collect.ensure_dirs")
    def test_run_returns_dict_on_failure(self, mock_dirs, mock_collect):
        mock_collect.side_effect = RuntimeError("network error")

        from ashare_data.collect import run

        result = run(date_str="2026-01-01")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    def test_no_sentiment_in_signature(self):
        from ashare_data.collect import run

        sig = inspect.signature(run)
        param_names = set(sig.parameters.keys())
        self.assertNotIn("run_sentiment", param_names)
        self.assertNotIn("sentiment_model", param_names)
        self.assertNotIn("sentiment_timeout", param_names)

    def test_no_sentiment_import(self):
        import ashare_data.collect as mod
        source = inspect.getsource(mod)
        self.assertNotIn("sentiment_preprocess", source)


if __name__ == "__main__":
    unittest.main()
