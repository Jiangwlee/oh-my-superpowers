"""Tests for trend_scanner public API stability.

Covers: importability of reusable scan entrypoints for platform reuse.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))


class TestTrendScannerPublicApi(unittest.TestCase):
    """Public API tests for trend scanner."""

    def test_trend_scanner_exposes_reusable_scan_api(self) -> None:
        from ashare_data.fetchers.trend_scanner import scan_all

        self.assertTrue(callable(scan_all))


if __name__ == "__main__":
    unittest.main()
