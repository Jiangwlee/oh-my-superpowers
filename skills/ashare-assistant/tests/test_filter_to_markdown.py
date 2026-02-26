"""filter_to_markdown 模块测试。"""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.filter_to_markdown import _filter_recent_24h


class FilterRecent24hTest(unittest.TestCase):

    def _make_items(self, *offsets_hours: int) -> list[dict]:
        """生成距今 N 小时的新闻条目列表。"""
        now = datetime.now()
        return [
            {
                "title": f"news-{i}",
                "makeDate": (now - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for i, h in enumerate(offsets_hours)
        ]

    def test_keeps_items_within_24h(self):
        items = self._make_items(1, 12, 23)
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 3)

    def test_drops_items_older_than_24h(self):
        items = self._make_items(1, 25, 48)
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "news-0")

    def test_fallback_to_first_item_when_all_filtered(self):
        """全部超过 24h 时，返回最新1条（而不是空列表）。"""
        items = self._make_items(25, 30, 48)
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "news-0")

    def test_malformed_date_kept(self):
        """makeDate 格式错误时，保留该条目（宽容策略）。"""
        items = [{"title": "bad", "makeDate": "not-a-date"}]
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)

    def test_empty_list(self):
        self.assertEqual(_filter_recent_24h([], hours=24), [])

    def test_boundary_exactly_24h_is_kept(self):
        """恰好在 24h 边界上的条目应被保留（>= 语义）。"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        items = [{"title": "boundary", "makeDate": cutoff.strftime("%Y-%m-%d %H:%M:%S")}]
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)

    def test_missing_makedate_key_kept(self):
        """makeDate 键不存在（返回 None）时，宽容保留该条目。"""
        items = [{"title": "no-date"}]
        result = _filter_recent_24h(items, hours=24)
        self.assertEqual(len(result), 1)
