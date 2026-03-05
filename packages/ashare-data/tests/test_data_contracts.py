"""Contract checks for key JSON outputs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ashare_data.collect import _build_manifest
from ashare_data.fetchers.market_sentiment import MarketSentiment


class TestDataContracts(unittest.TestCase):
    """Schema/version and lineage contract checks."""

    def test_manifest_contains_schema_and_file_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "2026-03-05"
            raw = data_dir / "raw"
            filtered = data_dir / "filtered"
            raw.mkdir(parents=True, exist_ok=True)
            filtered.mkdir(parents=True, exist_ok=True)
            (raw / "run_id.json").write_text(
                json.dumps({"run_id": "RID-1"}, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (raw / "a.json").write_text(json.dumps([{"x": 1}], ensure_ascii=False), encoding="utf-8")
            (filtered / "a.md").write_text("# A\n", encoding="utf-8")

            manifest = _build_manifest(data_dir, run_result={"ok": True})
            self.assertEqual(manifest["schema_version"], "1.0")
            self.assertEqual(manifest["run_id"], "RID-1")
            self.assertGreaterEqual(len(manifest["files"]), 2)
            self.assertIn("sha256", manifest["files"][0])

    def test_postclose_output_has_schema_and_lineage(self) -> None:
        import ashare_data.post_close_decision_pipeline as mod

        def _bars(count: int) -> list[mod._KlineBar]:
            rows: list[mod._KlineBar] = []
            for i in range(count):
                close = 10.0 + i * 0.1
                rows.append(
                    mod._KlineBar(
                        date=f"2025-01-{(i % 28) + 1:02d}",
                        open=close - 0.05,
                        close=close,
                        high=close + 0.1,
                        low=close - 0.1,
                        volume=1000.0,
                    )
                )
            return rows

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "signals" / "post_close_decisions.json"
            state = Path(tmp) / "memory" / "post_close_state.json"
            with patch.object(mod, "_SIGNALS_DIR", out.parent), patch.object(mod, "_OUTPUT_FILE", out), patch.object(
                mod, "_STATE_FILE", state
            ), patch.object(
                mod, "_load_watchlist_active", return_value=[{"code": "600000", "name": "测试股", "status": "active"}]
            ), patch.object(
                mod, "_load_holdings", return_value={}
            ), patch.object(
                mod, "_load_state", return_value={}
            ), patch.object(
                mod, "_fetch_jrj_kline", side_effect=[_bars(180), _bars(80)]
            ), patch(
                "ashare_data.post_close_decision_pipeline.load_latest_run_id", return_value="RID-X"
            ):
                result = mod.run_pipeline()
            self.assertIn("schema_version", result)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["source_run_id"], "RID-X")
            self.assertIn("source_files", payload)

    def test_watchlist_output_has_schema_and_lineage(self) -> None:
        import ashare_data.watchlist_monitor as mod

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchlist_signals.json"
            with patch.object(mod, "_SIGNALS_DIR", path.parent), patch.object(mod, "_SIGNALS_FILE", path), patch(
                "ashare_data.watchlist_monitor.load_latest_run_id", return_value="RID-Y"
            ):
                mod._write_signals(
                    [],
                    MarketSentiment(limit_up=1, limit_down=2, danger_level="green", market_open=True),
                    source_files=["signals/post_close_decisions.json"],
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["source_run_id"], "RID-Y")
            self.assertEqual(payload["source_files"], ["signals/post_close_decisions.json"])


if __name__ == "__main__":
    unittest.main()
