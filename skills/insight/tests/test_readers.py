"""T1 测试：Session readers 基本功能验证。"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.models import MessageRole, Runtime
from scripts.readers.claude_reader import ClaudeReader, _extract_project_path
from scripts.readers.codex_reader import CodexReader, _extract_session_id as codex_session_id
from scripts.readers.pi_reader import PiReader, _decode_project_path, _extract_session_id as pi_session_id


class TestClaudeReader(unittest.TestCase):
    """Claude Code reader 测试。"""

    def setUp(self):
        self.reader = ClaudeReader()
        self.tmpdir = tempfile.mkdtemp()

    def test_parse_user_message(self):
        lines = [
            json.dumps({
                "type": "user",
                "message": {"role": "user", "content": "帮我写个函数"},
                "uuid": "msg-001",
                "timestamp": "2026-03-27T10:00:00Z",
            }),
        ]
        path = Path(self.tmpdir) / "test-session.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].role, MessageRole.USER)
        self.assertEqual(msgs[0].content, "帮我写个函数")
        self.assertEqual(msgs[0].session_id, "test-session")

    def test_parse_assistant_with_tool_calls(self):
        lines = [
            json.dumps({
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "让我读一下文件"},
                        {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "/tmp/test"}},
                    ],
                },
                "uuid": "msg-002",
                "timestamp": "2026-03-27T10:00:05Z",
            }),
        ]
        path = Path(self.tmpdir) / "test-session.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].role, MessageRole.ASSISTANT)
        self.assertEqual(msgs[0].content, "让我读一下文件")
        self.assertEqual(len(msgs[0].tool_calls), 1)
        self.assertEqual(msgs[0].tool_calls[0].name, "Read")

    def test_skip_non_message_types(self):
        lines = [
            json.dumps({"type": "progress", "data": {}, "timestamp": "2026-03-27T10:00:00Z"}),
            json.dumps({"type": "file-history-snapshot", "messageId": "x", "snapshot": {}}),
            json.dumps({"type": "system", "subtype": "api_error", "timestamp": "2026-03-27T10:00:00Z"}),
        ]
        path = Path(self.tmpdir) / "test-session.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 0)

    def test_extract_project_path(self):
        self.assertEqual(
            _extract_project_path("-home-bruce-Projects-oh-my-superpowers"),
            "/home/bruce/Projects/oh/my/superpowers",
        )


class TestCodexReader(unittest.TestCase):
    """Codex reader 测试。"""

    def setUp(self):
        self.reader = CodexReader()
        self.tmpdir = tempfile.mkdtemp()

    def test_parse_response_item(self):
        lines = [
            json.dumps({
                "type": "session_meta",
                "timestamp": "2026-03-27T10:00:00Z",
                "payload": {"id": "sess-1", "cwd": "/home/bruce/Projects/test"},
            }),
            json.dumps({
                "type": "response_item",
                "timestamp": "2026-03-27T10:00:01Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "hello codex"}],
                },
            }),
            json.dumps({
                "type": "response_item",
                "timestamp": "2026-03-27T10:00:05Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "我来帮你"},
                        {"type": "toolCall", "id": "tc1", "name": "bash", "arguments": {"cmd": "ls"}},
                    ],
                },
            }),
        ]
        path = Path(self.tmpdir) / "rollout-2026-03-27T10-00-00-sess-uuid.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, MessageRole.USER)
        self.assertEqual(msgs[0].content, "hello codex")
        self.assertEqual(msgs[1].role, MessageRole.ASSISTANT)
        self.assertEqual(len(msgs[1].tool_calls), 1)

    def test_session_id_extraction(self):
        sid = codex_session_id("rollout-2026-03-09T21-30-12-019cd2ca-7fe5-75c0-8653-b5d3a7d73eb9.jsonl")
        self.assertEqual(sid, "019cd2ca-7fe5-75c0-8653-b5d3a7d73eb9")


class TestPiReader(unittest.TestCase):
    """Pi reader 测试。"""

    def setUp(self):
        self.reader = PiReader()
        self.tmpdir = tempfile.mkdtemp()

    def test_parse_message(self):
        lines = [
            json.dumps({
                "type": "session",
                "version": 3,
                "id": "sess-pi",
                "timestamp": "2026-03-27T10:00:00Z",
                "cwd": "/home/bruce/Projects/test",
            }),
            json.dumps({
                "type": "message",
                "id": "msg-1",
                "timestamp": "2026-03-27T10:00:01Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "hello pi"}],
                },
            }),
            json.dumps({
                "type": "message",
                "id": "msg-2",
                "timestamp": "2026-03-27T10:00:05Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "let me think..."},
                        {"type": "text", "text": "好的"},
                        {"type": "toolCall", "id": "tc1", "name": "bash", "arguments": {}},
                    ],
                },
            }),
        ]
        path = Path(self.tmpdir) / "2026-03-27T10-00-00-000Z_test-uuid.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, MessageRole.USER)
        self.assertEqual(msgs[0].content, "hello pi")
        self.assertEqual(msgs[1].role, MessageRole.ASSISTANT)
        self.assertEqual(msgs[1].content, "好的")  # thinking 被跳过
        self.assertEqual(len(msgs[1].tool_calls), 1)

    def test_decode_project_path(self):
        self.assertEqual(
            _decode_project_path("--home-bruce-Projects-oh-my-superpowers--"),
            "/home/bruce/Projects/oh/my/superpowers",
        )

    def test_session_id_extraction(self):
        sid = pi_session_id("2026-03-25T15-09-44-730Z_d1d64fc7-ff63-4c5b-bc76-fdfb5520f91f.jsonl")
        self.assertEqual(sid, "d1d64fc7-ff63-4c5b-bc76-fdfb5520f91f")


if __name__ == "__main__":
    unittest.main()
