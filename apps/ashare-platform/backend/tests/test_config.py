"""Tests for backend runtime config."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestConfig(unittest.TestCase):
    """Config tests."""

    def _clear_env(self) -> None:
        for key in (
            "ASHARE_PLATFORM_HOME",
            "ASHARE_THEME_POOL_PROFILE",
            "ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH",
            "ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE",
            "ASHARE_THEME_SEMANTIC_ENRICH_ENABLED",
            "OPENAI_BASE_URL",
            "OPENAI_MODEL",
            "OPENAI_API_KEY",
        ):
            os.environ.pop(key, None)

    def test_runtime_paths_are_resolved(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            try:
                import app.core.config as config_module

                config_module.get_settings.cache_clear()
                settings = config_module.get_settings()
                self.assertTrue(settings.ephemeral_dir.exists())
                self.assertEqual(settings.database_path.name, "ashare_platform.db")
                self.assertEqual(settings.theme_pool_profile, "default")
                self.assertEqual(settings.theme_pool_min_trend_stock_count, 1)
                self.assertEqual(settings.theme_pool_min_core_trend_stock_count, 0)
                self.assertEqual(settings.theme_pool_weight_theme_strength, 1.0)
            finally:
                self._clear_env()
                config_module.get_settings.cache_clear()

    def test_theme_pool_scoring_settings_can_be_overridden(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT"] = "2"
            os.environ["ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT"] = "1"
            os.environ["ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH"] = "1.5"
            os.environ["ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT"] = "4"
            os.environ["ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT"] = "5"
            os.environ["ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE"] = "0.1"
            try:
                import app.core.config as config_module

                config_module.get_settings.cache_clear()
                settings = config_module.get_settings()
                self.assertEqual(settings.theme_pool_min_trend_stock_count, 2)
                self.assertEqual(settings.theme_pool_min_core_trend_stock_count, 1)
                self.assertEqual(settings.theme_pool_weight_theme_strength, 1.5)
                self.assertEqual(settings.theme_pool_weight_trend_stock_count, 4.0)
                self.assertEqual(settings.theme_pool_weight_core_trend_stock_count, 5.0)
                self.assertEqual(settings.theme_pool_weight_strongest_trend_score, 0.1)
            finally:
                self._clear_env()
                config_module.get_settings.cache_clear()

    def test_mainline_strict_profile_applies_expected_defaults(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["ASHARE_THEME_POOL_PROFILE"] = "mainline_strict"
            try:
                import app.core.config as config_module

                config_module.get_settings.cache_clear()
                settings = config_module.get_settings()
                self.assertEqual(settings.theme_pool_profile, "mainline_strict")
                self.assertEqual(settings.theme_pool_min_trend_stock_count, 2)
                self.assertEqual(settings.theme_pool_min_core_trend_stock_count, 1)
                self.assertEqual(settings.theme_pool_weight_theme_strength, 0.8)
                self.assertEqual(settings.theme_pool_weight_trend_stock_count, 2.5)
                self.assertEqual(settings.theme_pool_weight_core_trend_stock_count, 6.0)
                self.assertEqual(settings.theme_pool_weight_strongest_trend_score, 0.03)
            finally:
                self._clear_env()
                config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
