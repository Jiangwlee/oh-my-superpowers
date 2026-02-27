"""run_analysis 模块退役行为测试。"""

import os
import sys
import unittest
import unittest.mock as mock

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

from scripts import run_analysis


class RunAnalysisDeprecatedTest(unittest.TestCase):
    def test_deprecated_message_contains_openclaw_workflow(self):
        message = run_analysis._deprecated_message()
        self.assertIn("已废弃", message)
        self.assertIn("Openclaw", message)
        self.assertIn("market_review.md", message)
        self.assertIn("analysis/candidates.json", message)
        self.assertIn("trading_plan.md", message)

    def test_main_exit_code_is_2(self):
        with mock.patch.object(sys, "argv", ["run_analysis.py"]):
            with self.assertRaises(SystemExit) as ctx:
                run_analysis.main()
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
