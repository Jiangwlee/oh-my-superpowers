"""run_analysis 模块测试。"""
import os
import sys
import tempfile
import unittest
import unittest.mock as mock

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

from scripts.run_analysis import _run_opencode


class RunOpencodeIdempotencyTest(unittest.TestCase):

    def test_skip_if_output_exists_and_non_empty(self):
        """output_path 已存在且非空时，直接返回 True，不启动子进程。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            with open(output_path, "w") as f:
                f.write("# existing report\nsome content")
            result = _run_opencode(
                prompt="irrelevant",
                output_path=output_path,
                title="test",
                overwrite=False,
            )
            self.assertTrue(result)

    def test_no_skip_when_file_empty(self):
        """output_path 存在但为空时，不触发跳过逻辑（getsize == 0）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            open(output_path, "w").close()  # 空文件
            with mock.patch("scripts.run_analysis.subprocess.run", side_effect=FileNotFoundError):
                result = _run_opencode(
                    prompt="irrelevant",
                    output_path=output_path,
                    title="test",
                    overwrite=False,
                )
            self.assertFalse(result)

    def test_no_skip_when_overwrite_true(self):
        """overwrite=True 时即使文件存在也不触发跳过逻辑。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            with open(output_path, "w") as f:
                f.write("# existing")
            with mock.patch("scripts.run_analysis.subprocess.run", side_effect=FileNotFoundError):
                result = _run_opencode(
                    prompt="irrelevant",
                    output_path=output_path,
                    title="test",
                    overwrite=True,
                )
            self.assertFalse(result)


class StdoutRedirectTest(unittest.TestCase):

    def test_stdout_markdown_written_to_file(self):
        """opencode 输出 Markdown stdout 时，内容应写入 output_path。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            fake_stdout = "# 新闻情绪分析\n\n## 结论\n内容在这里"

            mock_result = mock.Mock()
            mock_result.returncode = 0
            mock_result.stdout = fake_stdout
            mock_result.stderr = ""

            with mock.patch("scripts.run_analysis.subprocess.run", return_value=mock_result):
                result = _run_opencode(
                    prompt="test",
                    output_path=output_path,
                    title="test-stdout",
                    overwrite=True,
                )

            self.assertTrue(result)
            with open(output_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("# 新闻情绪分析", content)

    def test_empty_stdout_returns_false(self):
        """stdout 为空时返回 False。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")

            mock_result = mock.Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""

            with mock.patch("scripts.run_analysis.subprocess.run", return_value=mock_result):
                result = _run_opencode(
                    prompt="test",
                    output_path=output_path,
                    title="test-empty",
                    overwrite=True,
                )

            self.assertFalse(result)

    def test_no_markdown_header_returns_false(self):
        """stdout 有内容但没有 # 标题时返回 False。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")

            mock_result = mock.Mock()
            mock_result.returncode = 0
            mock_result.stdout = "这是一段没有标题的文字\n没有 # 开头"
            mock_result.stderr = ""

            with mock.patch("scripts.run_analysis.subprocess.run", return_value=mock_result):
                result = _run_opencode(
                    prompt="test",
                    output_path=output_path,
                    title="test-no-header",
                    overwrite=True,
                )

            self.assertFalse(result)
