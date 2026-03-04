"""Tests for /ashare/collect endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestAshareCollect(unittest.TestCase):
    """POST /ashare/collect tests."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.ashare._run_collect")
    def test_collect_success(self, mock_run):
        mock_run.return_value = {
            "ok": True,
            "data_dir": "/tmp/test/2026-01-01",
            "collect": {"ok_count": 5, "error_count": 0},
            "filter": {"converted": 5},
        }
        resp = self.client.post("/ashare/collect", json={"date": "2026-01-01"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertIsNotNone(body["task_id"])
        self.assertIsNotNone(body["result"])

    @patch("task_runner.routers.ashare._run_collect")
    def test_collect_failure(self, mock_run):
        mock_run.return_value = {
            "ok": False,
            "error": "network timeout",
        }
        resp = self.client.post("/ashare/collect", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIsNotNone(body["error"])

    @patch("task_runner.routers.ashare._run_collect")
    def test_collect_exception(self, mock_run):
        mock_run.side_effect = Exception("unexpected crash")
        resp = self.client.post("/ashare/collect", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("unexpected crash", body["error"])


if __name__ == "__main__":
    unittest.main()
