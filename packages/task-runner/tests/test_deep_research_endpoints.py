"""Tests for deep-research endpoints."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestDeepResearchCollect(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.deep_research._run_collect")
    def test_collect_success(self, mock_run):
        mock_run.return_value = {
            "ok": True,
            "stocks": [
                {"code": "002050", "name": "三花智控", "status": "collected"},
            ],
            "collected_count": 1,
            "skipped_count": 0,
            "total_targets": 1,
        }
        resp = self.client.post("/ashare/deep-research/collect", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["result"]["collected_count"], 1)

    @patch("task_runner.routers.deep_research._run_collect")
    def test_collect_exception(self, mock_run):
        mock_run.side_effect = Exception("crash")
        resp = self.client.post("/ashare/deep-research/collect", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")


class TestDeepResearchData(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.deep_research._run_load_data")
    def test_data_found(self, mock_load):
        mock_load.return_value = {
            "code": "002050",
            "name": "三花智控",
            "raw_em": {"latest_posts": []},
            "raw_tgb": {"quotes_posts": []},
            "has_brief": False,
        }
        resp = self.client.get("/ashare/deep-research/data", params={"code": "002050"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["result"]["code"], "002050")

    @patch("task_runner.routers.deep_research._run_load_data")
    def test_data_not_found(self, mock_load):
        mock_load.return_value = None
        resp = self.client.get("/ashare/deep-research/data", params={"code": "999999"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("not_found", body["error"])


class TestDeepResearchSaveReport(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.deep_research._run_save_report")
    def test_save_success(self, mock_save):
        mock_save.return_value = {
            "code": "002050",
            "saved_at": "2026-03-04 16:00:00",
        }
        resp = self.client.post(
            "/ashare/deep-research/save-report",
            json={"code": "002050", "report": "# 深研报告"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.deep_research._run_save_report")
    def test_save_exception(self, mock_save):
        mock_save.side_effect = Exception("disk full")
        resp = self.client.post(
            "/ashare/deep-research/save-report",
            json={"code": "002050", "report": "# test"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")


if __name__ == "__main__":
    unittest.main()
