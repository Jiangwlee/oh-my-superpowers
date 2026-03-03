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
                    }
                ]
            }
        }

        bars = trend_scanner.fetch_jrj_daily_kline("600000", range_num=60, timeout=5.0)

        self.assertEqual(len(bars), 1)
        self.assertAlmostEqual(bars[0]["open"], 10.12)
        self.assertAlmostEqual(bars[0]["close"], 10.56)
        self.assertAlmostEqual(bars[0]["high"], 10.80)
        self.assertAlmostEqual(bars[0]["low"], 10.00)


if __name__ == "__main__":
    unittest.main()
