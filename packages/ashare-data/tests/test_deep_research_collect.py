"""Tests for deep_research_collect service."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ashare_data.deep_research_collect import collect_deep_research
from ashare_data.deep_research import DeepResearchArchive


class TestCollectDeepResearch(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.archive_dir = Path(self.tmpdir) / "deep_research"
        self.data_dir = Path(self.tmpdir) / "data" / "2026-03-04"

        # Create fake trend_scan.json
        raw_dir = self.data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        trend_data = {
            "all_results": [
                {"code": "002050", "name": "三花智控", "is_uptrend": True, "star_rating": 5},
                {"code": "600519", "name": "贵州茅台", "is_uptrend": True, "star_rating": 4},
                {"code": "000001", "name": "平安银行", "is_uptrend": False, "star_rating": 2},
            ]
        }
        (raw_dir / "trend_scan.json").write_text(
            json.dumps(trend_data, ensure_ascii=False), encoding="utf-8"
        )

    @patch("ashare_data.deep_research_collect._fetch_em_data")
    @patch("ashare_data.deep_research_collect._fetch_tgb_data")
    @patch("ashare_data.deep_research_collect._load_watchlist_codes")
    @patch("ashare_data.deep_research_collect._find_latest_data_dir")
    def test_collects_new_stocks(self, mock_find_dir, mock_wl, mock_tgb, mock_em):
        mock_find_dir.return_value = self.data_dir
        mock_wl.return_value = []
        mock_em.return_value = {"code": "002050", "latest_posts": []}
        mock_tgb.return_value = {"full_code": "sz002050", "quotes_posts": []}

        result = collect_deep_research(archive_dir=self.archive_dir)

        self.assertTrue(result["ok"])
        self.assertGreater(result["collected_count"], 0)
        collected_codes = [s["code"] for s in result["stocks"] if s["status"] == "collected"]
        self.assertIn("002050", collected_codes)

    @patch("ashare_data.deep_research_collect._fetch_em_data")
    @patch("ashare_data.deep_research_collect._fetch_tgb_data")
    @patch("ashare_data.deep_research_collect._load_watchlist_codes")
    @patch("ashare_data.deep_research_collect._find_latest_data_dir")
    def test_skips_fresh_stocks(self, mock_find_dir, mock_wl, mock_tgb, mock_em):
        mock_find_dir.return_value = self.data_dir
        mock_wl.return_value = []
        mock_em.return_value = {"code": "002050"}
        mock_tgb.return_value = {"full_code": "sz002050"}

        # First collect
        collect_deep_research(archive_dir=self.archive_dir)
        # Second collect — should skip
        result = collect_deep_research(archive_dir=self.archive_dir)
        skipped_codes = [s["code"] for s in result["stocks"] if s["status"] == "skipped"]
        self.assertIn("002050", skipped_codes)

    @patch("ashare_data.deep_research_collect._fetch_em_data")
    @patch("ashare_data.deep_research_collect._fetch_tgb_data")
    @patch("ashare_data.deep_research_collect._load_watchlist_codes")
    @patch("ashare_data.deep_research_collect._find_latest_data_dir")
    def test_force_recollects(self, mock_find_dir, mock_wl, mock_tgb, mock_em):
        mock_find_dir.return_value = self.data_dir
        mock_wl.return_value = []
        mock_em.return_value = {"code": "002050"}
        mock_tgb.return_value = {"full_code": "sz002050"}

        collect_deep_research(archive_dir=self.archive_dir)
        result = collect_deep_research(archive_dir=self.archive_dir, force=True)
        collected_codes = [s["code"] for s in result["stocks"] if s["status"] == "collected"]
        self.assertIn("002050", collected_codes)

    @patch("ashare_data.deep_research_collect._load_watchlist_codes")
    @patch("ashare_data.deep_research_collect._find_latest_data_dir")
    def test_no_data_dir_returns_error(self, mock_find_dir, mock_wl):
        mock_find_dir.return_value = None
        mock_wl.return_value = []
        result = collect_deep_research(archive_dir=self.archive_dir)
        self.assertFalse(result["ok"])

    @patch("ashare_data.deep_research_collect._fetch_em_data")
    @patch("ashare_data.deep_research_collect._fetch_tgb_data")
    @patch("ashare_data.deep_research_collect._load_watchlist_codes")
    @patch("ashare_data.deep_research_collect._find_latest_data_dir")
    def test_watchlist_stocks_included(self, mock_find_dir, mock_wl, mock_tgb, mock_em):
        mock_find_dir.return_value = self.data_dir
        mock_wl.return_value = [{"code": "300750", "name": "宁德时代"}]
        mock_em.return_value = {"code": "300750"}
        mock_tgb.return_value = {"full_code": "sz300750"}

        result = collect_deep_research(archive_dir=self.archive_dir)
        all_codes = [s["code"] for s in result["stocks"]]
        self.assertIn("300750", all_codes)


if __name__ == "__main__":
    unittest.main()
