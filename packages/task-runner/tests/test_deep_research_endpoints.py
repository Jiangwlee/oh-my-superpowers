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
    def test_data_found_json(self, mock_load):
        """测试默认 JSON 格式返回"""
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
    def test_data_found_markdown(self, mock_load):
        """测试 Markdown 格式返回"""
        mock_load.return_value = "# 三花智控 (002050)\n\n## 基本信息"
        resp = self.client.get(
            "/ashare/deep-research/data",
            params={"code": "002050", "format": "markdown"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertIsInstance(body["result"], str)
        self.assertIn("# 三花智控", body["result"])

    @patch("task_runner.routers.deep_research._run_load_data")
    def test_data_invalid_format(self, mock_load):
        """测试无效 format 参数"""
        resp = self.client.get(
            "/ashare/deep-research/data",
            params={"code": "002050", "format": "xml"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("invalid_format", body["error"])

    @patch("task_runner.routers.deep_research._run_load_data")
    def test_data_not_found(self, mock_load):
        """测试股票不存在的情况"""
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
