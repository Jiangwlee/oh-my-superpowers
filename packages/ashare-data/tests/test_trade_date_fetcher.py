import sys
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.fetchers.trade_date import fetch_trade_date


class TradeDateFetcherTest(unittest.TestCase):
    @mock.patch("ashare_data.fetchers.trade_date.cache_set")
    @mock.patch("ashare_data.fetchers.trade_date.cache_get", return_value=None)
    @mock.patch("ashare_data.fetchers.trade_date.http_json")
    def test_fetch_trade_date_uses_post_response(
        self,
        mock_http_json: mock.Mock,
        _mock_cache_get: mock.Mock,
        _mock_cache_set: mock.Mock,
    ) -> None:
        mock_http_json.return_value = {"data": {"td": 20260319}}

        result = fetch_trade_date()

        self.assertEqual(result, "20260319")
        mock_http_json.assert_called_once_with(
            url="https://gateway.jrj.com/quot-feed/tradedate",
            method="POST",
            headers={
                "Origin": "https://summary.jrj.com.cn",
                "Referer": "https://summary.jrj.com.cn/",
            },
        )


if __name__ == "__main__":
    unittest.main()
