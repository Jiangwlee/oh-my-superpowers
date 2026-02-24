import sys
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.validate_output as validate_output


class ValidateOutputTest(unittest.TestCase):
    def test_validate_payload_success(self) -> None:
        payload = {
            "run_id": "20260220-v1.0-103000",
            "as_of_date": "2026-02-20",
            "market": {"regime": "strong"},
            "funding": {"data_degraded": False},
            "candidates": [
                {
                    "code": "688272",
                    "name": "联影医疗",
                    "score": 4.2,
                    "action": "buy",
                    "thesis_short": "趋势延续",
                    "risk_note": "分歧日回撤",
                }
            ],
            "risk_flags": {
                "data_degraded": False,
                "output_schema_invalid": False,
                "strategy_version_fallback": False,
            },
        }

        result = validate_output.validate_candidate_payload(payload)
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_validate_payload_fails_on_invalid_enum(self) -> None:
        payload = {
            "run_id": "20260220-v1.0-103000",
            "as_of_date": "2026-02-20",
            "market": {"regime": "sideways"},
            "funding": {"data_degraded": False},
            "candidates": [{"code": "688272", "name": "联影医疗", "score": 4.2, "action": "long"}],
            "risk_flags": {"output_schema_invalid": False},
        }

        result = validate_output.validate_candidate_payload(payload)
        self.assertFalse(result["ok"])
        self.assertGreaterEqual(len(result["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
