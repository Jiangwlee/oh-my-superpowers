"""美股行情抓取模块单元测试。"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILL_ROOT = Path(__file__).parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))


class UsMarketFetcherTest(unittest.TestCase):
    """测试 fetch_us_market() 的输出结构和降级行为。"""

    def _make_mock_ticker(self, prev_close: float, current_price: float) -> MagicMock:
        """构造一个模拟的 yfinance Ticker 对象。"""
        ticker = MagicMock()
        ticker.fast_info = MagicMock()
        ticker.fast_info.previous_close = prev_close
        ticker.fast_info.last_price = current_price
        ticker.fast_info.market_state = "CLOSED"
        return ticker

    @patch("scripts.fetchers.us_market.yf")
    def test_output_schema(self, mock_yf):
        """输出 JSON 必须包含 fetched_at / market_status / indices / tech_stocks。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(100.0, 102.0)

        result = fetch_us_market()

        self.assertIn("fetched_at", result)
        self.assertIn("market_status", result)
        self.assertIn("indices", result)
        self.assertIn("tech_stocks", result)

    @patch("scripts.fetchers.us_market.yf")
    def test_indices_content(self, mock_yf):
        """indices 必须包含纳斯达克、道琼斯、标普500、VIX，且有 change_pct。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(100.0, 103.0)

        result = fetch_us_market()
        tickers = {item["ticker"] for item in result["indices"]}
        self.assertIn("^IXIC", tickers)
        self.assertIn("^DJI", tickers)
        self.assertIn("^GSPC", tickers)
        self.assertIn("^VIX", tickers)

        for item in result["indices"]:
            self.assertIn("change_pct", item)
            self.assertIn("name_cn", item)

    @patch("scripts.fetchers.us_market.yf")
    def test_tech_stocks_content(self, mock_yf):
        """tech_stocks 必须包含 NVDA/AAPL/TSLA/MSFT/GOOG/META，且有 a_share_sectors。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(200.0, 196.0)

        result = fetch_us_market()
        tickers = {item["ticker"] for item in result["tech_stocks"]}
        for sym in ("NVDA", "AAPL", "TSLA", "MSFT", "GOOG", "META"):
            self.assertIn(sym, tickers)

        for item in result["tech_stocks"]:
            self.assertIsInstance(item["a_share_sectors"], list)
            self.assertGreater(len(item["a_share_sectors"]), 0)

    @patch("scripts.fetchers.us_market.yf")
    def test_change_pct_calculation(self, mock_yf):
        """涨跌幅计算：(current - prev) / prev * 100，保留2位小数。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(100.0, 102.0)

        result = fetch_us_market()
        for item in result["indices"] + result["tech_stocks"]:
            self.assertAlmostEqual(item["change_pct"], 2.0, places=1)

    @patch("scripts.fetchers.us_market.yf")
    def test_graceful_degradation_on_error(self, mock_yf):
        """单个 ticker 抓取失败时，不影响其他标的，change_pct 设为 None。"""
        from scripts.fetchers.us_market import fetch_us_market

        def side_effect(sym):
            if sym == "NVDA":
                raise RuntimeError("network error")
            return self._make_mock_ticker(100.0, 101.0)

        mock_yf.Ticker.side_effect = side_effect

        result = fetch_us_market()
        nvda_items = [i for i in result["tech_stocks"] if i["ticker"] == "NVDA"]
        self.assertEqual(len(nvda_items), 1)
        self.assertIsNone(nvda_items[0]["change_pct"])

        other = [i for i in result["tech_stocks"] if i["ticker"] != "NVDA"]
        for item in other:
            self.assertIsNotNone(item["change_pct"])

    def test_yfinance_unavailable(self):
        """yfinance 未安装时返回空结构，market_status 为 unavailable，包含 error 字段。"""
        import scripts.fetchers.us_market as m

        original_yf = m.yf
        original_available = m._YF_AVAILABLE
        try:
            m.yf = None
            m._YF_AVAILABLE = False
            from scripts.fetchers.us_market import fetch_us_market

            result = fetch_us_market()
            self.assertEqual(result["market_status"], "unavailable")
            self.assertIn("error", result)
            self.assertEqual(result["indices"], [])
            self.assertEqual(result["tech_stocks"], [])
        finally:
            m.yf = original_yf
            m._YF_AVAILABLE = original_available


if __name__ == "__main__":
    unittest.main()
