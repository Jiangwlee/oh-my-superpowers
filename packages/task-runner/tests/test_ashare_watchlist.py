"""Tests for /ashare/watchlist endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestAshareWatchlist(unittest.TestCase):
    """POST /ashare/watchlist tests."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.ashare._run_watchlist")
    def test_watchlist_success(self, mock_run):
        mock_run.return_value = {
            "status": "ok", "message": "", "market": {}, "signals": [],
        }
        resp = self.client.post("/ashare/watchlist", json={"force": True})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.ashare._run_watchlist")
    def test_watchlist_skipped(self, mock_run):
        mock_run.return_value = {
            "status": "skipped", "message": "非交易时段", "market": {}, "signals": [],
        }
        resp = self.client.post("/ashare/watchlist", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # skipped is not error, so status = success
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.ashare._run_watchlist")
    def test_watchlist_exception(self, mock_run):
        mock_run.side_effect = Exception("crash")
        resp = self.client.post("/ashare/watchlist", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")


if __name__ == "__main__":
    unittest.main()
