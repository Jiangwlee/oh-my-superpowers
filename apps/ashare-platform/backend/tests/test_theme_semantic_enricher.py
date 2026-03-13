"""Tests for OpenAI-compatible theme semantic enricher."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestThemeSemanticEnricher(unittest.TestCase):
    """Theme semantic enricher tests."""

    def test_openai_enricher_parses_json_and_applies_semantic_fields(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:10000/v1"
            os.environ["OPENAI_MODEL"] = "test-model"
            try:
                import app.core.config as config_module
                from app.services.theme_semantic_enricher import create_theme_semantic_enricher

                config_module.get_settings.cache_clear()

                def fake_request(url: str, payload: dict, headers: dict) -> dict:
                    self.assertEqual(url, "http://127.0.0.1:10000/v1/chat/completions")
                    self.assertEqual(payload["model"], "test-model")
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": (
                                        '{"market_attitude":"认可度高","theme_stage":"middle",'
                                        '"summary":"主线延续","stock_comments":{"000001":"龙头强势"}}'
                                    )
                                }
                            }
                        ]
                    }

                enrich = create_theme_semantic_enricher(request_fn=fake_request)
                theme, stocks = enrich(
                    {
                        "theme_name": "深海科技",
                        "theme_strength": 9.0,
                        "theme_score": 18.0,
                        "trend_stock_count": 2,
                        "core_trend_stock_count": 1,
                        "evidence_json": {},
                    },
                    [
                        {
                            "code": "000001",
                            "name": "平安银行",
                            "role": "leader",
                            "is_core": True,
                            "rank_in_theme": 1,
                            "trend_score": 88.0,
                            "star_rating": 4,
                            "emotion_level": 3,
                            "comment": None,
                        }
                    ],
                )

                self.assertEqual(theme["market_attitude"], "认可度高")
                self.assertEqual(theme["theme_stage"], "middle")
                self.assertEqual(theme["summary"], "主线延续")
                self.assertEqual(stocks[0]["comment"], "龙头强势")
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                os.environ.pop("OPENAI_BASE_URL", None)
                os.environ.pop("OPENAI_MODEL", None)
                config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
