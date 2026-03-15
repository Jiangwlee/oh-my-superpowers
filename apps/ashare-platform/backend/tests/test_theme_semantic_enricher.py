"""Tests for OpenAI-compatible theme semantic enricher."""

from __future__ import annotations

import json
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

    def test_openai_enricher_prompt_includes_emotion_fact_context(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:10000/v1"
            os.environ["OPENAI_MODEL"] = "test-model"
            try:
                import app.core.config as config_module
                from app.services.theme_semantic_enricher import create_theme_semantic_enricher

                config_module.get_settings.cache_clear()

                def fake_request(url: str, payload: dict, headers: dict) -> dict:
                    prompt = payload["messages"][1]["content"]
                    self.assertIn("识别末端风险优先于判断中段回调机会", prompt)
                    self.assertIn("请在 summary 中简要说明判断过程", prompt)
                    input_json = prompt.split("Input:\n", 1)[1]
                    parsed = json.loads(input_json)
                    self.assertEqual(parsed["market_emotion"]["limit_down_count"], 13)
                    self.assertEqual(parsed["theme_emotion"]["theme_cycle_hint"], "bad_divergence")
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"market_attitude":"退潮预警","theme_stage":"late","summary":"高位风险抬升"}'
                                }
                            }
                        ]
                    }

                enrich = create_theme_semantic_enricher(request_fn=fake_request)
                theme, _ = enrich(
                    {
                        "theme_name": "风电",
                        "theme_strength": 12.0,
                        "theme_score": 24.0,
                        "trend_stock_count": 3,
                        "core_trend_stock_count": 1,
                        "evidence_json": {},
                        "market_emotion_json": {"limit_down_count": 13, "blowup_rate": 0.23},
                        "theme_emotion_json": {"theme_cycle_hint": "bad_divergence", "limit_up_num_3d_delta": -4},
                    },
                    [],
                )
                self.assertEqual(theme["theme_stage"], "late")
                self.assertEqual(theme["market_attitude"], "退潮预警")
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                os.environ.pop("OPENAI_BASE_URL", None)
                os.environ.pop("OPENAI_MODEL", None)
                config_module.get_settings.cache_clear()

    def test_openai_enricher_prompt_allows_middle_when_core_support_survives(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:10000/v1"
            os.environ["OPENAI_MODEL"] = "test-model"
            try:
                import app.core.config as config_module
                from app.services.theme_semantic_enricher import create_theme_semantic_enricher

                config_module.get_settings.cache_clear()

                def fake_request(url: str, payload: dict, headers: dict) -> dict:
                    prompt = payload["messages"][1]["content"]
                    self.assertIn("如果市场转弱但题材核心承接稳定、并非恶性分歧，可保留为 middle", prompt)
                    self.assertIn("summary should be concise Chinese text and include a brief reasoning summary", prompt)
                    input_json = prompt.split("Input:\n", 1)[1]
                    parsed = json.loads(input_json)
                    self.assertEqual(parsed["theme_emotion"]["theme_cycle_hint"], "main_rise")
                    self.assertEqual(parsed["theme_emotion"]["leader_board_max"], 5)
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"market_attitude":"强分歧但核心仍强","theme_stage":"middle","summary":"高位分歧但未转退潮"}'
                                }
                            }
                        ]
                    }

                enrich = create_theme_semantic_enricher(request_fn=fake_request)
                theme, _ = enrich(
                    {
                        "theme_name": "风电",
                        "theme_strength": 12.0,
                        "theme_score": 24.0,
                        "trend_stock_count": 4,
                        "core_trend_stock_count": 2,
                        "evidence_json": {},
                        "market_emotion_json": {"limit_down_count": 10, "blowup_rate": 0.18, "cycle_stage_hint": "weakening"},
                        "theme_emotion_json": {
                            "theme_cycle_hint": "main_rise",
                            "leader_board_max": 5,
                            "leader_continuity_score": 6.5,
                            "limit_up_num_3d_delta": 2,
                        },
                    },
                    [],
                )
                self.assertEqual(theme["theme_stage"], "middle")
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                os.environ.pop("OPENAI_BASE_URL", None)
                os.environ.pop("OPENAI_MODEL", None)
                config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
