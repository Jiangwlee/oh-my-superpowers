import json
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.decision_logger as decision_logger


class DecisionLoggerTest(unittest.TestCase):
    def test_append_decision_log_success(self) -> None:
        payload = {
            "run_id": "20260220-v1.0-103000",
            "as_of_date": "2026-02-20",
            "market": {"regime": "neutral"},
            "candidates": [
                {"code": "000001", "name": "平安银行", "score": 3.8, "action": "watch"},
                {"code": "300750", "name": "宁德时代", "score": 4.6, "action": "buy"},
            ],
            "risk_flags": {"data_degraded": False, "output_schema_invalid": False},
        }

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "candidates.json"
            log_path = Path(tmp) / "decision_log.jsonl"
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = decision_logger.append_decision_log(input_path, log_path)
            self.assertTrue(result["ok"])
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["run_id"], payload["run_id"])
            self.assertEqual(record["market_regime"], "neutral")
            self.assertIsNone(record["outcome"]["t1"])

    def test_skip_on_schema_invalid_flag(self) -> None:
        payload = {
            "run_id": "20260220-v1.0-103000",
            "as_of_date": "2026-02-20",
            "market": {"regime": "neutral"},
            "candidates": [{"code": "000001", "name": "平安银行", "score": 3.8, "action": "watch"}],
            "risk_flags": {"output_schema_invalid": True},
        }

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "candidates.json"
            log_path = Path(tmp) / "decision_log.jsonl"
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = decision_logger.append_decision_log(input_path, log_path)
            self.assertFalse(result["ok"])
            self.assertFalse(log_path.exists())


if __name__ == "__main__":
    unittest.main()
