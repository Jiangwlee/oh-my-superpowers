import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.fetchers.market_breadth import fetch_market_breadth, fetch_market_breadth_for_date


class MarketBreadthTest(unittest.TestCase):
    @patch("ashare_data.fetchers.market_breadth.fetch_sohu_zdt_history")
    def test_fetch_market_breadth_for_date_prefers_sohu_history(self, mock_fetch_sohu_zdt_history):
        mock_fetch_sohu_zdt_history.return_value = [
            {
                "trade_date": "2026-03-20",
                "shanghai": {"advance_count": 308, "flat_count": 21, "decline_count": 1978},
                "shenzhen": {"advance_count": 312, "flat_count": 21, "decline_count": 2553},
                "beijing": {"advance_count": 42, "flat_count": 3, "decline_count": 255},
            }
        ]

        result = fetch_market_breadth_for_date("20260320")

        self.assertEqual(result.trade_date, "2026-03-20")
        self.assertEqual(result.advance_count, 662)
        self.assertEqual(result.flat_count, 45)
        self.assertEqual(result.decline_count, 4786)
        self.assertEqual(result.universe_total, 5493)
        self.assertIsNone(result.zdfb_bins)

    @patch("ashare_data.fetchers.market_breadth.fetch_indexflash_via_cdp")
    @patch("ashare_data.fetchers.market_breadth.http_json")
    def test_falls_back_to_cdp_when_http_fails(self, mock_http_json, mock_fetch_indexflash_via_cdp):
        mock_http_json.side_effect = RuntimeError("403")
        mock_fetch_indexflash_via_cdp.return_value = {
            "zdfb_data": {"zdfb": [1, 2, 3], "znum": 2, "dnum": 3}
        }

        result = fetch_market_breadth()

        self.assertEqual(result.advance_count, 2)
        self.assertEqual(result.decline_count, 3)
        self.assertEqual(result.flat_count, 1)
        self.assertEqual(result.universe_total, 6)

    @patch("ashare_data.fetchers.market_breadth.fetch_indexflash_via_cdp")
    @patch("ashare_data.fetchers.market_breadth.http_json")
    def test_uses_http_result_without_cdp_when_available(self, mock_http_json, mock_fetch_indexflash_via_cdp):
        mock_http_json.return_value = {
            "zdfb_data": {"zdfb": [10, 20, 30], "znum": 15, "dnum": 40}
        }

        result = fetch_market_breadth()

        self.assertEqual(result.advance_count, 15)
        self.assertEqual(result.decline_count, 40)
        self.assertEqual(result.flat_count, 5)
        mock_fetch_indexflash_via_cdp.assert_not_called()

    @patch("ashare_data.fetchers.market_breadth.fetch_sohu_zdt_history")
    @patch("ashare_data.fetchers.market_breadth.fetch_market_breadth")
    def test_fetch_market_breadth_for_date_falls_back_when_sohu_misses(
        self,
        mock_fetch_market_breadth,
        mock_fetch_sohu_zdt_history,
    ):
        mock_fetch_sohu_zdt_history.return_value = []
        mock_fetch_market_breadth.return_value = type(
            "Breadth",
            (),
            {
                "trade_date": None,
                "advance_count": 1,
                "decline_count": 2,
                "flat_count": 3,
                "zdfb_bins": [1, 2, 3],
                "universe_total": 6,
            },
        )()

        result = fetch_market_breadth_for_date("2026-03-20")

        self.assertEqual(result.trade_date, "2026-03-20")
        self.assertEqual(result.advance_count, 1)
        mock_fetch_market_breadth.assert_called_once()


if __name__ == "__main__":
    unittest.main()
