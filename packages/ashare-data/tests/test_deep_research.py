"""Tests for deep_research archive module."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ashare_data.deep_research import (
    DeepResearchArchive,
    DeepResearchTarget,
    normalize_full_code,
)


class TestNormalizeFullCode(unittest.TestCase):
    def test_six_digit_sz(self):
        self.assertEqual(normalize_full_code("002050"), "sz002050")

    def test_six_digit_sh(self):
        self.assertEqual(normalize_full_code("600519"), "sh600519")

    def test_already_prefixed(self):
        self.assertEqual(normalize_full_code("sz002050"), "sz002050")

    def test_short_code_passthrough(self):
        self.assertEqual(normalize_full_code("123"), "123")


class TestArchiveIndex(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.archive = DeepResearchArchive(Path(self.tmpdir))

    def test_empty_index(self):
        index = self.archive.load_index()
        self.assertEqual(index, {"stocks": {}, "last_updated": None})

    def test_save_and_load_index(self):
        self.archive.update_index("002050", "三花智控")
        index = self.archive.load_index()
        self.assertIn("002050", index["stocks"])
        entry = index["stocks"]["002050"]
        self.assertEqual(entry["name"], "三花智控")
        self.assertEqual(entry["collect_count"], 1)
        self.assertIsNotNone(entry["last_collected_at"])

    def test_update_increments_count(self):
        self.archive.update_index("002050", "三花智控")
        self.archive.update_index("002050", "三花智控")
        index = self.archive.load_index()
        self.assertEqual(index["stocks"]["002050"]["collect_count"], 2)


class TestArchiveNeedsUpdate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.archive = DeepResearchArchive(Path(self.tmpdir))

    def test_new_stock_needs_update(self):
        self.assertTrue(self.archive.needs_update("002050"))

    def test_fresh_stock_skipped(self):
        self.archive.update_index("002050", "三花智控")
        self.assertFalse(self.archive.needs_update("002050"))

    def test_stale_stock_needs_update(self):
        self.archive.update_index("002050", "三花智控")
        # Patch the timestamp to 8 days ago
        index = self.archive.load_index()
        index["stocks"]["002050"]["last_collected_at"] = "2026-02-24 10:00:00"
        self.archive._save_index(index)
        self.assertTrue(self.archive.needs_update("002050"))

    def test_force_ignores_freshness(self):
        self.archive.update_index("002050", "三花智控")
        self.assertTrue(self.archive.needs_update("002050", force=True))


class TestArchiveSaveData(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.archive = DeepResearchArchive(Path(self.tmpdir))

    def test_save_and_load_raw_data(self):
        em_data = {"code": "002050", "latest_posts": []}
        tgb_data = {"full_code": "sz002050", "quotes_posts": []}
        self.archive.save_raw_data("002050", "三花智控", em_data, tgb_data)
        loaded = self.archive.load_raw_data("002050")
        self.assertEqual(loaded["code"], "002050")
        self.assertEqual(loaded["raw_em"]["code"], "002050")
        self.assertEqual(loaded["raw_tgb"]["full_code"], "sz002050")

    def test_load_missing_stock_returns_none(self):
        self.assertIsNone(self.archive.load_raw_data("999999"))


class TestArchiveSaveReport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.archive = DeepResearchArchive(Path(self.tmpdir))

    def test_save_and_read_report(self):
        self.archive.save_raw_data("002050", "三花智控", {}, {})
        report = "# 002050 深研报告\n\n内容..."
        self.archive.save_report("002050", report)
        stock_dir = Path(self.tmpdir) / "002050"
        self.assertTrue((stock_dir / "brief.md").exists())
        self.assertEqual((stock_dir / "brief.md").read_text(encoding="utf-8"), report)
        # index 应更新 last_brief_at
        index = self.archive.load_index()
        self.assertIsNotNone(index["stocks"]["002050"]["last_brief_at"])

    def test_save_report_missing_stock_creates_dir(self):
        report = "# test"
        self.archive.save_report("002050", report)
        self.assertTrue((Path(self.tmpdir) / "002050" / "brief.md").exists())


class TestArchiveLoadData(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.archive = DeepResearchArchive(Path(self.tmpdir))

    def test_load_data_with_brief(self):
        self.archive.save_raw_data("002050", "三花智控", {"a": 1}, {"b": 2})
        self.archive.save_report("002050", "# report")
        loaded = self.archive.load_raw_data("002050")
        self.assertTrue(loaded["has_brief"])

    def test_load_data_without_brief(self):
        self.archive.save_raw_data("002050", "三花智控", {"a": 1}, {"b": 2})
        loaded = self.archive.load_raw_data("002050")
        self.assertFalse(loaded["has_brief"])


if __name__ == "__main__":
    unittest.main()
