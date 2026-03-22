"""trend_scanner 回归测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ashare_data.fetchers import trend_scanner


class TestFetchJrjDailyKline(unittest.TestCase):
    """验证 JRJ 日K解析不会触发 NameError。"""

    @patch("ashare_data.fetchers.trend_scanner.cache_set")
    @patch("ashare_data.fetchers.trend_scanner.cache_get", return_value=None)
    @patch("ashare_data.fetchers.trend_scanner.http_json")
    def test_fetch_jrj_daily_kline_parses_fields(
        self,
        mock_http_json,
        _mock_cache_get,
        _mock_cache_set,
    ) -> None:
        mock_http_json.return_value = {
            "data": {
                "kline": [
                    {
                        "nTime": 20260303,
                        "nOpenPx": "10.12",
                        "nLastPx": "10.56",
                        "nHighPx": "10.80",
                        "nLowPx": "10.00",
                        "llVolume": "1234500",
                        "llValue": "34567890",
                    },
                    {
                        "nTime": 20260304,
                        "nOpenPx": "10.60",
                        "nLastPx": "10.80",
                        "nHighPx": "10.98",
                        "nLowPx": "10.40",
                        "llVolume": "2234500",
                        "llValue": "45678900",
                    },
                ]
            }
        }

        bars = trend_scanner.fetch_jrj_daily_kline("600000", range_num=60, timeout=5.0)

        self.assertEqual(len(bars), 2)
        self.assertAlmostEqual(bars[0]["open"], 10.12)
        self.assertAlmostEqual(bars[0]["close"], 10.56)
        self.assertAlmostEqual(bars[0]["high"], 10.80)
        self.assertAlmostEqual(bars[0]["low"], 10.00)
        self.assertAlmostEqual(bars[0]["amount"], 34567890.0)
        self.assertIsNone(bars[0]["change_pct"])
        self.assertAlmostEqual(bars[1]["amount"], 45678900.0)
        self.assertAlmostEqual(bars[1]["change_pct"], 2.27, places=2)


class TestFetchEastmoneyPopularityRank(unittest.TestCase):
    """验证东方财富人气榜 fetcher 的 top_n 语义。"""

    @patch("ashare_data.fetchers.trend_scanner.fetch_eastmoney_top_rank_xuangu")
    def test_fetch_eastmoney_popularity_rank_caps_top_n_at_4000(self, mock_xuangu) -> None:
        mock_xuangu.return_value = [{"code": "000001", "sc": "SZ000001", "rank": 1, "name": "平安银行"}]

        result = trend_scanner.fetch_eastmoney_popularity_rank(top_n=5000, timeout=5.0)

        mock_xuangu.assert_called_once_with(top_n=4000, timeout=5.0)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
