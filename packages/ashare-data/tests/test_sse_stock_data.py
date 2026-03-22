import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.fetchers.sse_stock_data import (
    fetch_sse_activity_main,
    fetch_sse_overview_day,
    fetch_sse_statistic,
)


def _jsonp(data: dict) -> str:
    return f"jsonpCallback({data})".replace("'", '"')


class SseStockDataTest(unittest.TestCase):
    @patch("ashare_data.fetchers.sse_stock_data.http_text")
    def test_fetch_sse_overview_day_uses_expected_sql_id_and_referer(self, mock_http_text):
        mock_http_text.return_value = _jsonp(
            {
                "result": [
                    {"TRADE_DATE": "20260320", "PRODUCT_CODE": "17", "TRADE_AMT": "9667.1"},
                    {"TRADE_DATE": "20260320", "PRODUCT_CODE": "01", "TRADE_AMT": "7197.0"},
                ]
            }
        )
        result = fetch_sse_overview_day("2026-03-20")
        self.assertEqual(result["trade_date"], "20260320")
        self.assertEqual(result["by_product_code"]["17"]["TRADE_AMT"], "9667.1")
        requested_url = mock_http_text.call_args.args[0]
        self.assertIn("sqlId=COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C", requested_url)
        self.assertIn("SEARCH_DATE=2026-03-20", requested_url)
        self.assertEqual(
            mock_http_text.call_args.kwargs["headers"]["Referer"],
            "https://www.sse.com.cn/market/stockdata/overview/day/",
        )

    @patch("ashare_data.fetchers.sse_stock_data.http_text")
    def test_fetch_sse_statistic_builds_product_name_index(self, mock_http_text):
        mock_http_text.return_value = _jsonp(
            {
                "result": [
                    {"TRADE_DATE": "20260320", "PRODUCT_NAME": "股票", "SECURITY_NUM": "2348"},
                    {"TRADE_DATE": "20260320", "PRODUCT_NAME": "主板", "SECURITY_NUM": "1744"},
                    {"TRADE_DATE": "20260320", "PRODUCT_NAME": "科创板", "SECURITY_NUM": "604"},
                ]
            }
        )
        result = fetch_sse_statistic()
        self.assertEqual(result["trade_date"], "20260320")
        self.assertEqual(result["by_product_name"]["科创板"]["SECURITY_NUM"], "604")
        requested_url = mock_http_text.call_args.args[0]
        self.assertIn("sqlId=COMMON_SSE_SJ_GPSJ_GPSJZM_TJSJ_L", requested_url)

    @patch("ashare_data.fetchers.sse_stock_data.http_text")
    def test_fetch_sse_activity_main_returns_rows_and_total(self, mock_http_text):
        mock_http_text.return_value = _jsonp(
            {
                "pageHelp": {"total": 20, "pageSize": 20},
                "result": [
                    {"TRADE_DATE": "20260320", "RN": "1", "SEC_CODE": "601868", "SEC_NAME": "中国能建"}
                ],
            }
        )
        result = fetch_sse_activity_main("2026-03-20", sort_by="TRADE_AMT_DESC", page_size=20)
        self.assertEqual(result["trade_date"], "20260320")
        self.assertEqual(result["sort_by"], "TRADE_AMT_DESC")
        self.assertEqual(result["total"], 20)
        self.assertEqual(result["rows"][0]["SEC_CODE"], "601868")
        requested_url = mock_http_text.call_args.args[0]
        self.assertIn("sqlId=COMMON_SSE_SJ_GPSJ_HYGPM_L", requested_url)
        self.assertIn("TRADE_AMT_DESC=1", requested_url)

    def test_fetch_sse_activity_main_rejects_unsupported_sort_field(self):
        with self.assertRaises(ValueError):
            fetch_sse_activity_main(sort_by="BAD_SORT")


if __name__ == "__main__":
    unittest.main()
