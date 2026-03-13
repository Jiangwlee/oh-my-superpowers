import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.platform_context as platform_context


class PlatformContextTest(unittest.TestCase):
    def test_sync_platform_context_writes_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            responses = {
                ("/trend-pool/daily", "trade_date=2026-03-13"): [{"code": "000001"}],
                ("/theme-pool/daily", "trade_date=2026-03-13"): [{"theme_name": "深海科技"}],
                ("/market-reviews/daily/2026-03-13", ""): {"trade_date": "2026-03-13"},
                ("/theme-pool/daily/%E6%B7%B1%E6%B5%B7%E7%A7%91%E6%8A%80/stocks", "trade_date=2026-03-13"): [{"code": "000001"}],
            }

            def fake_fetch(base_url: str, path: str, params: dict | None = None):
                key = (path, "" if not params else f"trade_date={params['trade_date']}")
                return responses[key]

            with mock.patch.object(platform_context, "_fetch_json", side_effect=fake_fetch):
                result = platform_context.sync_platform_context(
                    trade_date="2026-03-13",
                    base_url="http://127.0.0.1:8000",
                    output_dir=tmp,
                )

            report_dir = Path(tmp) / "report"
            self.assertTrue((report_dir / "platform_trend_pool.json").exists())
            self.assertTrue((report_dir / "platform_theme_pool.json").exists())
            self.assertTrue((report_dir / "platform_theme_stocks.json").exists())
            self.assertTrue((report_dir / "platform_market_review.json").exists())
            payload = json.loads((report_dir / "platform_theme_pool.json").read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["theme_name"], "深海科技")
            self.assertEqual(result["trade_date"], "2026-03-13")


if __name__ == "__main__":
    unittest.main()
