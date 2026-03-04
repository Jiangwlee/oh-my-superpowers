"""Tests for health endpoint."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from task_runner.app import app


class TestHealth(unittest.TestCase):
    """Health endpoint tests."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
