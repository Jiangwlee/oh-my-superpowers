import json
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.run_deep_research_batch as batch


class RunDeepResearchBatchTest(unittest.TestCase):
    def test_normalize_full_code(self) -> None:
        self.assertEqual(batch.normalize_full_code("002413"), "sz002413")
        self.assertEqual(batch.normalize_full_code("600519"), "sh600519")
        self.assertEqual(batch.normalize_full_code("sz002413"), "sz002413")

    def test_run_stock_stops_after_failure(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(cmd: list[str], timeout_sec: float) -> batch.CommandResult:
            calls.append(cmd)
            if "collect_taoguba_stock.py" in cmd[-1] or any("collect_taoguba_stock.py" in x for x in cmd):
                return batch.CommandResult(returncode=1, stdout="", stderr="boom")
            return batch.CommandResult(returncode=0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            result = batch.run_stock_deep_research(
                code="002413",
                output_dir=Path(tmp),
                skill_root=Path(tmp),
                per_stock_timeout_sec=60.0,
                command_runner=fake_runner,
            )

        self.assertEqual(result["status"], "error")
        self.assertGreaterEqual(len(calls), 2)
        step_names = [s["name"] for s in result["steps"]]
        self.assertIn("eastmoney", step_names)
        self.assertIn("taoguba", step_names)
        self.assertNotIn("compact", step_names)

    def test_run_stock_stops_after_timeout(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(cmd: list[str], timeout_sec: float) -> batch.CommandResult:
            calls.append(cmd)
            if any("collect_eastmoney_guba.py" in x for x in cmd):
                raise TimeoutError("step timeout")
            return batch.CommandResult(returncode=0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            result = batch.run_stock_deep_research(
                code="002413",
                output_dir=Path(tmp),
                skill_root=Path(tmp),
                per_stock_timeout_sec=30.0,
                command_runner=fake_runner,
            )

        self.assertEqual(result["status"], "timeout")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["name"], "eastmoney")

    def test_write_timing_report(self) -> None:
        rows = [
            {"code": "002413", "status": "ok", "elapsed_sec": 1.23, "steps": []},
            {"code": "600519", "status": "timeout", "elapsed_sec": 12.0, "steps": []},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            report_path = batch.write_timing_report(output_dir=output_dir, rows=rows)
            self.assertTrue(report_path.exists())
            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["summary"]["total"], 2)
        self.assertEqual(payload["summary"]["ok"], 1)
        self.assertEqual(payload["summary"]["timeout"], 1)
        self.assertEqual(len(payload["stocks"]), 2)


if __name__ == "__main__":
    unittest.main()
