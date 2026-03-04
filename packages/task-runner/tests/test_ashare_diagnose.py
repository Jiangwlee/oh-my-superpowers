"""Tests for /ashare/diagnose endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestAshareDiagnose(unittest.TestCase):
    """POST /ashare/diagnose tests."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.ashare._run_diagnose")
    def test_diagnose_success(self, mock_run):
        mock_run.return_value = {"ok": True, "updated_t1": 2, "updated_t5": 1, "dry_run": False}
        resp = self.client.post("/ashare/diagnose", json={"dry_run": True})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.ashare._run_diagnose")
    def test_diagnose_exception(self, mock_run):
        mock_run.side_effect = Exception("file not found")
        resp = self.client.post("/ashare/diagnose", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("file not found", body["error"])


if __name__ == "__main__":
    unittest.main()
