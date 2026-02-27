import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import ashare_data.fetchers.funding as funding


class FundingFetcherTest(unittest.TestCase):
    def test_build_result_from_rows(self) -> None:
        rows = [
            {"code": "300750", "name": "宁德时代", "net_inflow": 8.2},
            {"code": "600519", "name": "贵州茅台", "net_inflow": 6.5},
        ]

        result = funding._build_funding_result(
            northbound_net=12.3, top_rows=rows, degraded=False
        )
        self.assertEqual(result["northbound_net"], 12.3)
        self.assertFalse(result["data_degraded"])
        self.assertEqual(len(result["main_force_top20"]), 2)
        self.assertIn("trend_candidates_funding", result)
        self.assertEqual(result["trend_candidates_funding"], [])

    def test_fallback_result_is_degraded(self) -> None:
        result = funding._build_funding_result(
            northbound_net=0.0, top_rows=[], degraded=True
        )
        self.assertTrue(result["data_degraded"])
        self.assertEqual(result["main_force_top20"], [])

    def test_fetch_funding_for_codes_uses_cache(self) -> None:
        """fetch_funding_for_codes 应从模块缓存返回指定代码的资金数据。"""
        # 直接写入缓存模拟 fetch_funding() 已执行
        funding._RANK_CACHE = [
            {"code": "603163", "name": "圣晖集成", "net_inflow": 5.1, "rank": 1},
            {"code": "000738", "name": "航发控制", "net_inflow": 3.2, "rank": 2},
            {"code": "002169", "name": "智光电气", "net_inflow": -1.0, "rank": 3},
        ]

        result = funding.fetch_funding_for_codes(["603163", "002169", "999999"])
        codes = [r["code"] for r in result]
        self.assertIn("603163", codes)
        self.assertIn("002169", codes)
        self.assertNotIn("999999", codes)
        # 按 net_inflow 降序
        self.assertEqual(codes[0], "603163")

    def test_fetch_funding_for_codes_empty_cache(self) -> None:
        """缓存为空时应返回空列表，不报错。"""
        funding._RANK_CACHE = []
        result = funding.fetch_funding_for_codes(["603163"])
        self.assertEqual(result, [])

    def test_fetch_funding_for_codes_empty_input(self) -> None:
        """传入空列表时应返回空列表。"""
        funding._RANK_CACHE = [
            {"code": "603163", "name": "圣晖集成", "net_inflow": 5.1, "rank": 1},
        ]
        result = funding.fetch_funding_for_codes([])
        self.assertEqual(result, [])

    def test_build_result_contains_funding_indicator(self) -> None:
        """结果应包含 funding_indicator 字段，默认为 '3日'。"""
        result = funding._build_funding_result(
            northbound_net=0.0,
            top_rows=[],
            degraded=False,
        )
        self.assertEqual(result["funding_indicator"], "3日")

    def test_build_result_with_today_top20(self) -> None:
        """传入 today_top20 时，结果应包含 today_top10（截断为10条）。"""
        today = [
            {"code": f"{i:06d}", "name": f"股票{i}", "net_inflow": float(i)}
            for i in range(15)
        ]
        result = funding._build_funding_result(
            northbound_net=0.0,
            top_rows=[],
            degraded=False,
            today_top20=today,
        )
        self.assertIn("today_top10", result)
        self.assertEqual(len(result["today_top10"]), 10)

    def test_build_result_without_today_top20(self) -> None:
        """不传入 today_top20 时，结果不应包含 today_top10。"""
        result = funding._build_funding_result(
            northbound_net=0.0,
            top_rows=[],
            degraded=False,
        )
        self.assertNotIn("today_top10", result)

    def test_parse_main_force_rows_with_3day_indicator(self) -> None:
        """_parse_main_force_rows 应正确处理3日列名。"""
        import pandas as pd  # type: ignore

        df = pd.DataFrame(
            {
                "代码": ["300750", "600519"],
                "名称": ["宁德时代", "贵州茅台"],
                "3日主力净流入-净额": [800000000, 500000000],
            }
        )
        rows = funding._parse_main_force_rows(df, indicator="3日", update_cache=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["code"], "300750")
        self.assertAlmostEqual(rows[0]["net_inflow"], 8.0, places=1)
        # 缓存应被更新
        self.assertEqual(len(funding._RANK_CACHE), 2)

    def test_parse_main_force_rows_no_cache_update(self) -> None:
        """update_cache=False 时不应修改 _RANK_CACHE。"""
        import pandas as pd  # type: ignore

        funding._RANK_CACHE = [
            {"code": "000001", "name": "平安银行", "net_inflow": 1.0, "rank": 1}
        ]
        df = pd.DataFrame(
            {
                "代码": ["300750"],
                "名称": ["宁德时代"],
                "今日主力净流入-净额": [900000000],
            }
        )
        rows = funding._parse_main_force_rows(df, indicator="今日", update_cache=False)
        self.assertEqual(len(rows), 1)
        # 缓存应保持原样
        self.assertEqual(len(funding._RANK_CACHE), 1)
        self.assertEqual(funding._RANK_CACHE[0]["code"], "000001")


class FundingHttpPathTest(unittest.TestCase):
    """测试新 HTTP 路径（mock http_text）。"""

    def _northbound_response(self, net_deal_amt: float | None = 3130.79) -> str:
        """构造北向资金接口响应体。"""
        row = {
            "MUTUAL_TYPE": "006",
            "TRADE_DATE": "2026-02-24 00:00:00",
            "NET_DEAL_AMT": net_deal_amt,
        }
        return json.dumps(
            {
                "result": {"data": [row], "pages": 1, "count": 1},
                "success": True,
                "message": "ok",
            }
        )

    def _fundflow_response(
        self,
        diff: list[dict] | None = None,
        total: int = 2,
    ) -> str:
        """构造个股主力净流入接口响应体。"""
        if diff is None:
            diff = [
                {
                    "f12": "300750",
                    "f14": "宁德时代",
                    "f62": 2750000000,
                    "f267": 3000000000,
                },
                {
                    "f12": "600519",
                    "f14": "贵州茅台",
                    "f62": 1500000000,
                    "f267": 1800000000,
                },
            ]
        return json.dumps({"data": {"diff": diff, "total": total}, "rc": 0})

    def test_fetch_northbound_net_normal(self) -> None:
        """正常响应时应正确换算 NET_DEAL_AMT ÷ 100 = 亿元。"""
        with patch(
            "ashare_data.fetchers.funding.http_text",
            return_value=self._northbound_response(3130.79),
        ):
            result = funding._fetch_northbound_net()
        # 3130.79 ÷ 100 = 31.308
        self.assertAlmostEqual(result, 31.308, places=2)

    def test_fetch_northbound_net_empty_rows(self) -> None:
        """接口返回空数据时应返回 0.0。"""
        body = json.dumps({"result": {"data": [], "pages": 0}, "success": True})
        with patch("ashare_data.fetchers.funding.http_text", return_value=body):
            result = funding._fetch_northbound_net()
        self.assertEqual(result, 0.0)

    def test_fetch_northbound_net_null_value(self) -> None:
        """NET_DEAL_AMT 为 None 时应返回 0.0。"""
        with patch(
            "ashare_data.fetchers.funding.http_text",
            return_value=self._northbound_response(None),
        ):
            result = funding._fetch_northbound_net()
        self.assertEqual(result, 0.0)

    def test_fetch_northbound_net_http_error(self) -> None:
        """HTTP 异常时应安全降级返回 0.0。"""
        with patch(
            "ashare_data.fetchers.funding.http_text", side_effect=OSError("timeout")
        ):
            result = funding._fetch_northbound_net()
        self.assertEqual(result, 0.0)

    def test_fetch_fund_flow_rank_normal(self) -> None:
        """正常响应时应正确解析排名数据并换算净流入（÷1e8=亿）。"""
        with patch(
            "ashare_data.fetchers.funding.http_text", return_value=self._fundflow_response()
        ):
            rows = funding._fetch_fund_flow_rank(indicator="3日")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["code"], "300750")
        self.assertEqual(rows[0]["name"], "宁德时代")
        # f267=3000000000 ÷ 1e8 = 30.0 亿
        self.assertAlmostEqual(rows[0]["net_inflow"], 30.0, places=1)
        self.assertEqual(rows[0]["rank"], 1)

    def test_fetch_fund_flow_rank_empty(self) -> None:
        """接口返回空数据时应返回空列表。"""
        body = json.dumps({"data": {"diff": [], "total": 0}, "rc": 0})
        with patch("ashare_data.fetchers.funding.http_text", return_value=body):
            rows = funding._fetch_fund_flow_rank(indicator="3日")
        self.assertEqual(rows, [])

    def test_fetch_fund_flow_rank_invalid_indicator(self) -> None:
        """不支持的 indicator 应返回空列表，不报错。"""
        rows = funding._fetch_fund_flow_rank(indicator="无效")
        self.assertEqual(rows, [])

    def test_fetch_fund_flow_rank_http_error(self) -> None:
        """HTTP 异常时应安全降级返回空列表。"""
        with patch(
            "ashare_data.fetchers.funding.http_text", side_effect=OSError("timeout")
        ):
            rows = funding._fetch_fund_flow_rank(indicator="今日")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
