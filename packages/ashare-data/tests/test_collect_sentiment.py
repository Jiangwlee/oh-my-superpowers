"""Tests for collect_sentiment deep-research target selection.

Covers: selecting targets only from buy signals and deduplicating by code.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from ashare_data.collect_sentiment import _build_deep_research_targets_from_signals


class DeepResearchTargetSelectionTest(unittest.TestCase):
    """深研目标只应来自买入信号。"""

    def test_only_buy_signals_are_selected(self) -> None:
        post_close_rows = [
            {"code": "000001", "name": "平安银行", "action": "open", "reason": "A"},
            {"code": "000002", "name": "万科A", "action": "hold", "reason": "B"},
            {"code": "000003", "name": "国农科技", "action": "add", "reason": "C"},
        ]
        watchlist_rows = [
            {"code": "000003", "name": "国农科技", "action_next_day": "buy_open_t1", "reason": "dup"},
            {"code": "000004", "name": "国华网安", "state": "ENTRY", "reason": "D"},
            {"code": "000005", "name": "世纪星源", "action_next_day": "wait_breakout", "reason": "E"},
        ]

        targets = _build_deep_research_targets_from_signals(post_close_rows, watchlist_rows)
        codes = [item.code for item in targets]

        self.assertEqual(codes, ["000001", "000003", "000004"])


if __name__ == "__main__":
    unittest.main()
