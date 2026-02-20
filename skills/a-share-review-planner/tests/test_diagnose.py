import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.diagnose as diagnose


class DiagnoseTest(unittest.TestCase):
    def test_process_updates_pending_t1(self) -> None:
        record = {
            "run_id": "20260219-v1.0-153000",
            "as_of_date": "2026-02-19",
            "market_regime": "strong",
            "candidates": [{"code": "300750", "name": "宁德时代", "score": 4.8, "action": "buy"}],
            "risk_flags": {"data_degraded": False},
            "outcome": {"t1": None, "t5": None, "written_at": None},
        }

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "decision_log.jsonl"
            feedback_path = Path(tmp) / "feedback.md"
            log_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

            with mock.patch("scripts.diagnose.fetch_candidate_t1_return", return_value=2.5):
                with mock.patch("scripts.diagnose.fetch_benchmark_t1_return", return_value=1.0):
                    result = diagnose.process_diagnose(
                        log_file=log_path,
                        feedback_file=feedback_path,
                        dry_run=False,
                        today="2026-02-20",
                    )

            self.assertTrue(result["ok"])
            updated = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(updated[0]["outcome"]["t1"], 2.5)
            self.assertEqual(updated[0]["outcome"]["benchmark_t1"], 1.0)
            self.assertTrue(feedback_path.exists())


if __name__ == "__main__":
    unittest.main()
