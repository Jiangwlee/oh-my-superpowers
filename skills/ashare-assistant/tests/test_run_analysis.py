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
