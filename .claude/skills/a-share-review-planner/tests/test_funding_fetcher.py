import sys
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.fetchers.funding as funding


class FundingFetcherTest(unittest.TestCase):
    def test_build_result_from_rows(self) -> None:
        rows = [
            {"code": "300750", "name": "宁德时代", "net_inflow": 8.2},
            {"code": "600519", "name": "贵州茅台", "net_inflow": 6.5},
        ]

        result = funding._build_funding_result(northbound_net=12.3, top_rows=rows, degraded=False)
        self.assertEqual(result["northbound_net"], 12.3)
        self.assertFalse(result["data_degraded"])
        self.assertEqual(len(result["main_force_top20"]), 2)
        self.assertIn("trend_candidates_funding", result)
        self.assertEqual(result["trend_candidates_funding"], [])

    def test_fallback_result_is_degraded(self) -> None:
        result = funding._build_funding_result(northbound_net=0.0, top_rows=[], degraded=True)
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


if __name__ == "__main__":
    unittest.main()
