"""Tests for building trend pool daily facts."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class _FakeTrendResult:
    def __init__(
        self,
        code: str,
        name: str,
        rank: int,
        score: float,
        *,
        is_uptrend: bool = True,
    ) -> None:
        self.code = code
        self.name = name
        self.rank = rank
        self.score = score
        self.is_uptrend = is_uptrend

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "name": self.name,
            "rank": self.rank,
            "source": "fake",
            "score_total_100": self.score,
            "star_rating": 4,
            "emotion_level": 3,
            "emotion_label": "中性",
            "trade_signal": "观察",
            "is_uptrend": self.is_uptrend,
            "gain_30_pct": 12.3,
            "gain_60_pct": 18.9,
            "holding_experience": "较好",
            "reason": "fake",
            "emotion_reason": "fake",
            "trade_signal_reason": "fake",
        }


class TestBuildTrendPool(unittest.TestCase):
    """Trend pool build tests."""

    def test_build_trend_pool_persists_only_uptrend_rows(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.pipelines.build_trend_pool import build_trend_pool

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

            result = build_trend_pool(
                trade_date="2026-03-13",
                fetch_candidates=lambda **_: [
                    {"code": "000001", "sc": "SZ000001", "name": "平安银行", "rank": 1, "from": "fake"},
                    {"code": "000002", "sc": "SZ000002", "name": "万科A", "rank": 2, "from": "fake"},
                ],
                scanner=lambda candidates: [
                    _FakeTrendResult("000001", "平安银行", 1, 88.0, is_uptrend=True),
                    _FakeTrendResult("000002", "万科A", 2, 77.0, is_uptrend=False),
                ],
            )
            self.assertEqual(result["rows_written"], 1)
            self.assertEqual(result["candidate_count"], 2)

            with session_module.open_session() as session:
                rows = session.query(TrendPoolDaily).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].code, "000001")

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
