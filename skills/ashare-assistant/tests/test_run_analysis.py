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
        """output_path 存在但为空时，不跳过（视为无效输出）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            open(output_path, "w").close()  # 空文件
            # mock subprocess.run 抛出 FileNotFoundError，模拟 opencode 不存在
            with mock.patch("subprocess.run", side_effect=FileNotFoundError):
                result = _run_opencode(
                    prompt="irrelevant",
                    output_path=output_path,
                    title="test",
                    overwrite=False,
                )
            self.assertFalse(result)  # opencode 命令不存在，失败

    def test_no_skip_when_overwrite_true(self):
        """overwrite=True 时即使文件存在也不跳过。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "result.md")
            with open(output_path, "w") as f:
                f.write("# existing")
            # mock subprocess.run 抛出 FileNotFoundError，模拟 opencode 不存在
            with mock.patch("subprocess.run", side_effect=FileNotFoundError):
                result = _run_opencode(
                    prompt="irrelevant",
                    output_path=output_path,
                    title="test",
                    overwrite=True,
                )
            self.assertFalse(result)  # opencode 命令不存在，失败
