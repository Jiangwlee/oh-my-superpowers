"""Tests for backend CLI dispatch."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestCli(unittest.TestCase):
    """CLI tests."""

    def test_cli_dispatches_build_trend_pool(self) -> None:
        from app.cli import main

        with patch("app.cli.run_build_trend_pool", return_value={"rows_written": 1}) as mocked:
            stdout = io.StringIO()
            with patch.object(sys, "argv", ["ashare-platform", "build-trend-pool", "--date", "2026-03-13"]):
                with redirect_stdout(stdout):
                    main()

        mocked.assert_called_once_with(trade_date="2026-03-13", max_rank=1000)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["rows_written"], 1)

    def test_cli_dispatches_build_emotion_facts(self) -> None:
        from app.cli import main

        with patch("app.cli.run_build_emotion_facts", return_value={"theme_rows_written": 2}) as mocked:
            stdout = io.StringIO()
            with patch.object(sys, "argv", ["ashare-platform", "build-emotion-facts", "--date", "2026-03-13"]):
                with redirect_stdout(stdout):
                    main()

        mocked.assert_called_once_with(trade_date="2026-03-13")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["theme_rows_written"], 2)


if __name__ == "__main__":
    unittest.main()
