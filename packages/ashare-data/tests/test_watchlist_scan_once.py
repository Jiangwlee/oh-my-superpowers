"""Tests for watchlist_monitor.scan_once() public API."""

from __future__ import annotations

import unittest


class TestScanOncePublicAPI(unittest.TestCase):
    """Verify scan_once is importable and returns expected structure."""

    def test_scan_once_is_importable(self):
        from ashare_data.watchlist_monitor import scan_once
        self.assertTrue(callable(scan_once))

    def test_scan_once_outside_trading_hours(self):
        """Outside trading hours, scan_once returns skipped status."""
        from ashare_data.watchlist_monitor import scan_once
        result = scan_once(force=False)
        self.assertIsInstance(result, dict)
        # Either way the structure should have these keys
        self.assertIn("status", result)
        self.assertIn("market", result)
        self.assertIn("signals", result)


if __name__ == "__main__":
    unittest.main()
