"""Tests for OpenAI-compatible market review semantic enricher."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestMarketReviewSemanticEnricher(unittest.TestCase):
    """Market review semantic enricher tests."""

    def test_openai_enricher_parses_summary_and_markdown(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:10000/v1"
            os.environ["OPENAI_MODEL"] = "test-model"
            try:
                import app.core.config as config_module
                from app.services.market_review_semantic_enricher import create_market_review_semantic_enricher

                config_module.get_settings.cache_clear()

                def fake_request(url: str, payload: dict, headers: dict) -> dict:
                    self.assertEqual(url, "http://127.0.0.1:10000/v1/chat/completions")
                    self.assertEqual(payload["model"], "test-model")
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": (
                                        '{"summary":"主线延续，情绪修复。",'
                                        '"report_markdown":"# 市场复盘\\n\\n主线延续，情绪修复。"}'
                                    )
                                }
                            }
                        ]
                    }

                enrich = create_market_review_semantic_enricher(request_fn=fake_request)
                row = enrich(
                    {
                        "trade_date": "2026-03-13",
                        "regime": "strong",
                        "position_guidance": "60-80%",
                        "main_themes_json": ["深海科技"],
                        "emerging_themes_json": [],
                        "fading_themes_json": [],
                        "report_markdown": "# 市场复盘 - 2026-03-13",
                    }
                )
                self.assertEqual(row["summary"], "主线延续，情绪修复。")
                self.assertIn("主线延续", row["report_markdown"])
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                os.environ.pop("OPENAI_BASE_URL", None)
                os.environ.pop("OPENAI_MODEL", None)
                config_module.get_settings.cache_clear()

    def test_openai_enricher_accepts_date_object_in_review_row(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:10000/v1"
            os.environ["OPENAI_MODEL"] = "test-model"
            try:
                import app.core.config as config_module
                from app.services.market_review_semantic_enricher import create_market_review_semantic_enricher

                config_module.get_settings.cache_clear()

                def fake_request(url: str, payload: dict, headers: dict) -> dict:
                    prompt = payload["messages"][1]["content"]
                    self.assertIn('"trade_date": "2026-03-13"', prompt)
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": (
                                        '{"summary":"情绪回暖。",'
                                        '"report_markdown":"# 市场复盘\\n\\n情绪回暖。"}'
                                    )
                                }
                            }
                        ]
                    }

                enrich = create_market_review_semantic_enricher(request_fn=fake_request)
                row = enrich(
                    {
                        "trade_date": date(2026, 3, 13),
                        "regime": "strong",
                        "position_guidance": "60-80%",
                        "main_themes_json": ["深海科技"],
                        "emerging_themes_json": [],
                        "fading_themes_json": [],
                        "report_markdown": "# 市场复盘 - 2026-03-13",
                    }
                )
                self.assertEqual(row["summary"], "情绪回暖。")
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                os.environ.pop("OPENAI_BASE_URL", None)
                os.environ.pop("OPENAI_MODEL", None)
                config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
