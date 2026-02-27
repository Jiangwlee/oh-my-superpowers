import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ashare_data import diagnose


class DiagnoseTest(unittest.TestCase):
    def _make_record(self, as_of_date: str, t1=None, t5=None) -> dict:
        return {
            "run_id": f"{as_of_date.replace('-','')}-v1.0-150000",
            "as_of_date": as_of_date,
            "market_regime": "strong",
            "candidates": [
                {"code": "300750", "name": "宁德时代", "score": 4.8, "action": "buy"},
                {"code": "000001", "name": "平安银行", "score": 3.2, "action": "watch"},
            ],
            "risk_flags": {"data_degraded": False},
            "outcome": {
                "t1": t1, "benchmark_t1": None, "excess_t1": None,
                "t5": t5, "benchmark_t5": None, "excess_t5": None,
                "written_at": None,
            },
        }

    def test_t1_fills_pending_record(self) -> None:
        """T+1 回填：t1=null 且日期满足条件时应写入结果。"""
        record = self._make_record("2026-02-19")

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "decision_log.jsonl"
            feedback_path = Path(tmp) / "feedback.md"
            log_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

            with mock.patch("ashare_data.diagnose.fetch_candidate_tn_return", return_value=2.5):
                with mock.patch("ashare_data.diagnose.fetch_benchmark_tn_return", return_value=1.0):
                    result = diagnose.process_diagnose(
                        log_file=log_path,
                        feedback_file=feedback_path,
                        dry_run=False,
                        today="2026-02-20",
                    )

            self.assertTrue(result["ok"])
            self.assertEqual(result["updated_t1"], 1)
            updated = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(updated[0]["outcome"]["t1"], 2.5)
            self.assertEqual(updated[0]["outcome"]["benchmark_t1"], 1.0)
            self.assertEqual(updated[0]["outcome"]["excess_t1"], 1.5)
            self.assertTrue(feedback_path.exists())

    def test_t5_fills_after_7_days(self) -> None:
        """T+5 回填：日期满足 ≥7 天条件时应写入 t5 结果。"""
        record = self._make_record("2026-02-10", t1=1.5)

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "decision_log.jsonl"
            feedback_path = Path(tmp) / "feedback.md"
            log_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

            with mock.patch("ashare_data.diagnose.fetch_candidate_tn_return", return_value=3.8):
                with mock.patch("ashare_data.diagnose.fetch_benchmark_tn_return", return_value=1.2):
                    result = diagnose.process_diagnose(
                        log_file=log_path,
                        feedback_file=feedback_path,
                        dry_run=False,
                        today="2026-02-20",
                    )

            self.assertTrue(result["ok"])
            self.assertEqual(result["updated_t5"], 1)
            updated = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(updated[0]["outcome"]["t5"], 3.8)
            self.assertEqual(updated[0]["outcome"]["benchmark_t5"], 1.2)

    def test_skips_record_with_no_buy_candidates(self) -> None:
        """没有 action=buy 候选的记录不应被处理。"""
        record = self._make_record("2026-02-19")
        record["candidates"] = [{"code": "000001", "name": "平安银行", "score": 3.0, "action": "watch"}]

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "decision_log.jsonl"
            feedback_path = Path(tmp) / "feedback.md"
            log_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

            with mock.patch("ashare_data.diagnose.fetch_candidate_tn_return", return_value=2.0):
                with mock.patch("ashare_data.diagnose.fetch_benchmark_tn_return", return_value=1.0):
                    result = diagnose.process_diagnose(
                        log_file=log_path,
                        feedback_file=feedback_path,
                        dry_run=True,
                        today="2026-02-20",
                    )

            self.assertTrue(result["ok"])
            self.assertEqual(result["updated_t1"], 0)

    def test_dry_run_does_not_write(self) -> None:
        """dry_run 模式不应写回文件或生成 feedback.md。"""
        record = self._make_record("2026-02-19")

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "decision_log.jsonl"
            feedback_path = Path(tmp) / "feedback.md"
            original = json.dumps(record, ensure_ascii=False) + "\n"
            log_path.write_text(original, encoding="utf-8")

            with mock.patch("ashare_data.diagnose.fetch_candidate_tn_return", return_value=2.0):
                with mock.patch("ashare_data.diagnose.fetch_benchmark_tn_return", return_value=1.0):
                    result = diagnose.process_diagnose(
                        log_file=log_path,
                        feedback_file=feedback_path,
                        dry_run=True,
                        today="2026-02-20",
                    )

            self.assertTrue(result["dry_run"])
            self.assertEqual(log_path.read_text(encoding="utf-8"), original)
            self.assertFalse(feedback_path.exists())


if __name__ == "__main__":
    unittest.main()
