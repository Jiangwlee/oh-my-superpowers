import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import ashare_data.core.cache as cache


class CacheTest(unittest.TestCase):
    def test_cache_set_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cache, "CACHE_DIR", Path(tmp) / "cache"):
                payload = {"a": 1, "b": "x"}
                cache.cache_set("taoguba", "hot_2026-02-24", payload, ttl_seconds=60)

                result = cache.cache_get("taoguba", "hot_2026-02-24")

            self.assertEqual(result, payload)

    def test_cache_get_expired_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cache, "CACHE_DIR", Path(tmp) / "cache"):
                cache.cache_set("news", "flash", {"items": []}, ttl_seconds=0)
                result = cache.cache_get("news", "flash")

            self.assertIsNone(result)

    def test_cache_cleanup_removes_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cache"
            old_dir = root / "news"
            old_dir.mkdir(parents=True, exist_ok=True)
            old_file = old_dir / "old.json"
            old_file.write_text(
                json.dumps(
                    {
                        "_cache_meta": {
                            "created_at": "2026-02-01T00:00:00+08:00",
                            "ttl_seconds": None,
                            "category": "news",
                            "key": "old",
                        },
                        "data": {"x": 1},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            now = time.time()
            old_ts = now - 9 * 24 * 3600
            Path(old_file).touch()
            import os

            os.utime(old_file, (old_ts, old_ts))

            with mock.patch.object(cache, "CACHE_DIR", root):
                removed = cache.cache_cleanup(max_age_days=7)

            self.assertGreaterEqual(removed["removed_files"], 1)
            self.assertFalse(old_file.exists())

    def test_cache_invalidate_single_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cache, "CACHE_DIR", Path(tmp) / "cache"):
                cache.cache_set("news", "k1", {"x": 1}, ttl_seconds=60)
                removed = cache.cache_invalidate("news", "k1")
                self.assertEqual(removed, 1)
                self.assertIsNone(cache.cache_get("news", "k1"))

    def test_trade_date_hybrid_keeps_kline_daily_even_if_ttl_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cache, "CACHE_DIR", Path(tmp) / "cache"):
                cache.cache_set("kline", "000001_daily_2026-02-24_80", {"bars": []}, ttl_seconds=0)
                result = cache.cache_get("kline", "000001_daily_2026-02-24_80")
            self.assertEqual(result, {"bars": []})

    def test_minute_kline_still_expires(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cache, "CACHE_DIR", Path(tmp) / "cache"):
                cache.cache_set("kline", "000001_minute_2026-02-24_241", {"bars": []}, ttl_seconds=0)
                result = cache.cache_get("kline", "000001_minute_2026-02-24_241")
            self.assertIsNone(result)

    def test_cache_cleanup_capacity_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cache"
            with mock.patch.object(cache, "CACHE_DIR", root):
                cache.cache_set("news", "a", {"blob": "x" * 200}, ttl_seconds=None)
                cache.cache_set("news", "b", {"blob": "x" * 200}, ttl_seconds=None)
                out = cache.cache_cleanup(max_age_days=7, max_total_bytes=250)
            self.assertGreaterEqual(out["removed_files"], 1)


if __name__ == "__main__":
    unittest.main()
