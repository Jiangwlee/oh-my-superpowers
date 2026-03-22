import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.fetchers.market_sentiment import fetch_market_sentiment, fetch_market_sentiment_for_date


def _mock_resp(trade_status_id: str, trade_status_name: str = "") -> dict:
    return {
        "data": {
            "trade_status": {"id": trade_status_id, "name": trade_status_name},
            "page": {"total": 12},
            "limit_down_count": {"today": {"num": 3}},
        }
    }


class MarketSentimentTest(unittest.TestCase):
    @patch("ashare_data.fetchers.market_sentiment.http_json")
    def test_market_open_for_morning_trade(self, mock_http_json):
        mock_http_json.return_value = _mock_resp("morning_trade", "交易中")
        result = fetch_market_sentiment()
        self.assertTrue(result.market_open)
        self.assertEqual(result.danger_level, "green")

    @patch("ashare_data.fetchers.market_sentiment.http_json")
    def test_market_open_for_afternoon_trade(self, mock_http_json):
        mock_http_json.return_value = _mock_resp("afternoon_trade", "交易中")
        result = fetch_market_sentiment()
        self.assertTrue(result.market_open)

    @patch("ashare_data.fetchers.market_sentiment.http_json")
    def test_market_closed_for_closed_status(self, mock_http_json):
        mock_http_json.return_value = _mock_resp("closed", "已收盘")
        result = fetch_market_sentiment()
        self.assertFalse(result.market_open)

    @patch("ashare_data.fetchers.market_sentiment.http_json")
    def test_fetch_market_sentiment_for_date_uses_requested_date(self, mock_http_json):
        mock_http_json.return_value = _mock_resp("closed", "已收盘")
        result = fetch_market_sentiment_for_date("20260313")
        self.assertEqual(result.limit_up, 12)
        self.assertEqual(result.limit_down, 3)
        requested_url = mock_http_json.call_args.kwargs["url"]
        self.assertIn("date=20260313", requested_url)

    @patch("ashare_data.fetchers.market_sentiment.http_json")
    def test_fetch_market_sentiment_for_date_computes_blowup_rate(self, mock_http_json):
        payload = _mock_resp("closed", "已收盘")
        payload["data"]["limit_up_count"] = {"today": {"num": 12, "history_num": 20, "open_num": 8, "rate": 0.6}}
        payload["data"]["limit_down_count"] = {"today": {"num": 3, "history_num": 5, "open_num": 2}}
        mock_http_json.return_value = payload
        result = fetch_market_sentiment_for_date("20260313")
        self.assertAlmostEqual(result.blowup_rate or 0.0, 0.4, places=6)
        self.assertAlmostEqual(result.seal_rate or 0.0, 0.6, places=6)
        self.assertEqual(result.limit_up_history_num, 20)
        self.assertEqual(result.limit_up_open_num, 8)
        self.assertEqual(result.limit_down_history_num, 5)
        self.assertEqual(result.limit_down_open_num, 2)


if __name__ == "__main__":
    unittest.main()
