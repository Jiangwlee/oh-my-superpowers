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

import scripts.core.cache as cache


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


if __name__ == "__main__":
    unittest.main()
