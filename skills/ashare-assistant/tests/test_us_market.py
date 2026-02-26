"""美股行情抓取模块单元测试。

覆盖范围：
- 输出 schema 完整性
- 指数 / 个股内容正确性
- 涨跌幅计算逻辑
- 网络失败时的降级行为
- market_status 时区判断
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))


# ---------------------------------------------------------------------------
# 辅助：构造腾讯财经 gtimg mock 响应
# ---------------------------------------------------------------------------


def _gtimg_body(syms: list[str], close: float, prev_close: float) -> bytes:
    """构造腾讯财经 gtimg 响应（GBK 编码）。

    字段（tilde 分隔，0-indexed）：
        [3] close  [4] prev_close  [32] change_pct
    """
    change_pct = (
        round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
    )
    lines = []
    for sym in syms:
        fields = ["200", "测试", sym, str(close), str(prev_close)]
        fields += ["0"] * 27  # fields 5..31
        fields.append(str(change_pct))  # field 32
        lines.append(f'v_{sym}="{chr(126).join(fields)}"')
    return "\n".join(lines).encode("gbk")


def _all_gtimg_syms() -> list[str]:
    """返回所有指数+个股的 gtimg 代码列表。"""
    from ashare_data.fetchers.us_market import _INDICES, _TECH_STOCKS

    return [c["gtimg_sym"] for c in _INDICES] + [c["gtimg_sym"] for c in _TECH_STOCKS]


class UsMarketFetcherTest(unittest.TestCase):
    """测试 fetch_us_market() 的输出结构、内容正确性和降级行为。"""

    def setUp(self):
        """每个测试前 patch cache_get/cache_set，避免命中旧缓存。"""
        self._cache_patcher = patch(
            "ashare_data.fetchers.us_market.cache_get", return_value=None
        )
        self._cache_set_patcher = patch("ashare_data.fetchers.us_market.cache_set")
        self._cache_patcher.start()
        self._cache_set_patcher.start()

    def tearDown(self):
        self._cache_patcher.stop()
        self._cache_set_patcher.stop()

    # ------------------------------------------------------------------
    # schema 完整性
    # ------------------------------------------------------------------

    def test_output_schema(self):
        """输出 JSON 必须包含 fetched_at / market_status / indices / tech_stocks。"""
        from ashare_data.fetchers.us_market import fetch_us_market

        with patch(
            "ashare_data.fetchers.us_market.http_bytes",
            return_value=_gtimg_body(_all_gtimg_syms(), 102.0, 100.0),
        ):
            result = fetch_us_market()

        self.assertIn("fetched_at", result)
        self.assertIn("market_status", result)
        self.assertIn("indices", result)
        self.assertIn("tech_stocks", result)

    # ------------------------------------------------------------------
    # 指数内容
    # ------------------------------------------------------------------

    def test_indices_content(self):
        """indices 必须包含纳斯达克/道琼斯/标普500/VIX，且有 change_pct / name_cn。"""
        from ashare_data.fetchers.us_market import fetch_us_market

        with patch(
            "ashare_data.fetchers.us_market.http_bytes",
            return_value=_gtimg_body(_all_gtimg_syms(), 103.0, 100.0),
        ):
            result = fetch_us_market()

        tickers = {item["ticker"] for item in result["indices"]}
        self.assertIn("^IXIC", tickers)
        self.assertIn("^DJI", tickers)
        self.assertIn("^GSPC", tickers)
        self.assertIn("^VIX", tickers)

        for item in result["indices"]:
            self.assertIn("change_pct", item)
            self.assertIn("name_cn", item)

    # ------------------------------------------------------------------
    # 个股内容
    # ------------------------------------------------------------------

    def test_tech_stocks_content(self):
        """tech_stocks 必须包含 NVDA/AAPL/TSLA/MSFT/GOOG/META，且有 a_share_sectors。"""
        from ashare_data.fetchers.us_market import fetch_us_market

        with patch(
            "ashare_data.fetchers.us_market.http_bytes",
            return_value=_gtimg_body(_all_gtimg_syms(), 196.0, 200.0),
        ):
            result = fetch_us_market()

        tickers = {item["ticker"] for item in result["tech_stocks"]}
        for sym in ("NVDA", "AAPL", "TSLA", "MSFT", "GOOG", "META"):
            self.assertIn(sym, tickers)

        for item in result["tech_stocks"]:
            self.assertIsInstance(item["a_share_sectors"], list)
            self.assertGreater(len(item["a_share_sectors"]), 0)

    # ------------------------------------------------------------------
    # 涨跌幅计算
    # ------------------------------------------------------------------

    def test_change_pct_calculation(self):
        """涨跌幅计算：(close - prev_close) / prev_close * 100，保留2位小数。"""
        from ashare_data.fetchers.us_market import fetch_us_market

        with patch(
            "ashare_data.fetchers.us_market.http_bytes",
            return_value=_gtimg_body(_all_gtimg_syms(), 102.0, 100.0),
        ):
            result = fetch_us_market()

        for item in result["indices"] + result["tech_stocks"]:
            self.assertAlmostEqual(item["change_pct"], 2.0, places=1)

    # ------------------------------------------------------------------
    # 降级行为：网络失败时所有字段为 None
    # ------------------------------------------------------------------

    def test_graceful_degradation_on_error(self):
        """gtimg 接口失败时，所有指数和个股的 change_pct 均为 None。"""
        from ashare_data.fetchers.us_market import fetch_us_market

        with patch(
            "ashare_data.fetchers.us_market.http_bytes",
            side_effect=RuntimeError("network error"),
        ):
            result = fetch_us_market()

        for item in result["indices"] + result["tech_stocks"]:
            self.assertIsNone(item["change_pct"])

    # ------------------------------------------------------------------
    # market_status 时区判断
    # ------------------------------------------------------------------

    def test_market_status_open(self):
        """美东时间周三 10:00 → open。"""
        from ashare_data.fetchers.us_market import _market_status_by_time

        # 2026-02-25 (Wed) 15:00 UTC = 美东冬令时 10:00 EST
        t = datetime(2026, 2, 25, 15, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_market_status_by_time(t), "open")

    def test_market_status_pre_market(self):
        """美东时间周三 07:00 → pre-market。"""
        from ashare_data.fetchers.us_market import _market_status_by_time

        # 2026-02-25 (Wed) 12:00 UTC = 美东冬令时 07:00 EST
        t = datetime(2026, 2, 25, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_market_status_by_time(t), "pre-market")

    def test_market_status_after_hours(self):
        """美东时间周三 17:00 → after-hours。"""
        from ashare_data.fetchers.us_market import _market_status_by_time

        # 2026-02-25 (Wed) 22:00 UTC = 美东冬令时 17:00 EST
        t = datetime(2026, 2, 25, 22, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_market_status_by_time(t), "after-hours")

    def test_market_status_closed_weekend(self):
        """周六 → closed。"""
        from ashare_data.fetchers.us_market import _market_status_by_time

        # 2026-02-28 (Sat) 15:00 UTC
        t = datetime(2026, 2, 28, 15, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_market_status_by_time(t), "closed")

    def test_market_status_closed_night(self):
        """美东时间 02:00 → closed。"""
        from ashare_data.fetchers.us_market import _market_status_by_time

        # 2026-02-25 (Wed) 07:00 UTC = 美东冬令时 02:00 EST
        t = datetime(2026, 2, 25, 7, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_market_status_by_time(t), "closed")


if __name__ == "__main__":
    unittest.main()
