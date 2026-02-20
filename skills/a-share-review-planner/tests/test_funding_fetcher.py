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

    def test_fallback_result_is_degraded(self) -> None:
        result = funding._build_funding_result(northbound_net=0.0, top_rows=[], degraded=True)
        self.assertTrue(result["data_degraded"])
        self.assertEqual(result["main_force_top20"], [])


if __name__ == "__main__":
    unittest.main()
