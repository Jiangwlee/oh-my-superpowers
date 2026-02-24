import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.core.shared as shared


class SharedHelpersTest(unittest.TestCase):
    def test_safe_float_and_int(self) -> None:
        self.assertEqual(shared.safe_float("12.3"), 12.3)
        self.assertEqual(shared.safe_float("", 1.5), 1.5)
        self.assertEqual(shared.safe_int("12.9"), 12)
        self.assertEqual(shared.safe_int(None, 7), 7)

    def test_norm_code(self) -> None:
        self.assertEqual(shared.norm_code("sz000001"), "000001")
        self.assertEqual(shared.norm_code("600000.SH"), "600000")
        self.assertEqual(shared.norm_code("1"), "000001")

    def test_parse_rules(self) -> None:
        self.assertAlmostEqual(shared.extract_pct_limit("单只不超过总仓位20%", 0.1), 0.2)
        self.assertEqual(shared.parse_range_to_pct("6-8成仓位"), (60.0, 80.0))
        self.assertEqual(shared.parse_range_to_pct("30-50%"), (30.0, 50.0))
        self.assertIsNone(shared.parse_range_to_pct("无区间"))

    def test_load_strategy_missing_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "missing.yaml")
            data = shared.load_strategy(path)
        self.assertEqual(data["strategy_version"], shared.DEFAULT_STRATEGY["strategy_version"])

    def test_determine_account_mode(self) -> None:
        self.assertEqual(shared.determine_account_mode(0, 0), "normal")
        self.assertEqual(shared.determine_account_mode(100, -35), "critical")
        self.assertEqual(shared.determine_account_mode(100, -11), "defensive")
        self.assertEqual(shared.determine_account_mode(100, 25), "growth")


if __name__ == "__main__":
    unittest.main()
