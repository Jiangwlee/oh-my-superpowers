"""Tests for OpenAI-compatible market review semantic enricher."""

from __future__ import annotations

import json
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

    def test_openai_enricher_prompt_requires_richer_trading_review_sections(self) -> None:
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
                    self.assertIn("市场情绪定位", prompt)
                    self.assertIn("主线与非主线", prompt)
                    self.assertIn("推演过程", prompt)
                    self.assertIn("交易结论", prompt)
                    self.assertIn("不要省略推演过程", prompt)
                    parsed = json.loads(prompt.split("Input:\n", 1)[1])
                    self.assertEqual(parsed["market_emotion"]["limit_down_count"], 13)
                    self.assertEqual(parsed["themes"][0]["theme_stage"], "middle")
                    self.assertEqual(parsed["themes"][1]["theme_stage"], "late")
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": (
                                        '{"summary":"情绪分歧加剧，聚焦可修复主线。",'
                                        '"report_markdown":"# 市场复盘\\n\\n## 市场情绪定位\\n\\n情绪分歧加剧。\\n\\n## 推演过程\\n\\n先看风险再看承接。\\n\\n## 交易结论\\n\\n只做核心主线。"}'
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
                        "main_themes_json": ["风电", "海工装备", "煤化工概念"],
                        "emerging_themes_json": [],
                        "fading_themes_json": ["绿色电力"],
                        "market_emotion_json": {"limit_down_count": 13, "blowup_rate": 0.23, "cycle_stage_hint": "weakening"},
                        "themes_json": [
                            {"theme_name": "风电", "theme_stage": "middle", "market_attitude": "情绪退潮但题材未崩"},
                            {"theme_name": "海工装备", "theme_stage": "late", "market_attitude": "情绪退潮，分歧加剧"},
                        ],
                        "trend_codes_json": ["600722", "002531"],
                        "report_markdown": "# 市场复盘 - 2026-03-13",
                    }
                )
                self.assertIn("## 市场情绪定位", row["report_markdown"])
                self.assertIn("## 推演过程", row["report_markdown"])
                self.assertIn("## 交易结论", row["report_markdown"])
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                os.environ.pop("OPENAI_BASE_URL", None)
                os.environ.pop("OPENAI_MODEL", None)
                config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
