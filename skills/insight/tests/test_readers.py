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
from scripts.readers.openclaw_reader import OpenClawReader, _extract_agent_name
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


class TestOpenClawReader(unittest.TestCase):
    """OpenClaw reader 测试。"""

    def setUp(self):
        self.reader = OpenClawReader()
        self.tmpdir = tempfile.mkdtemp()

    def test_parse_message(self):
        """测试基本消息解析（格式与 Pi v3 一致）。"""
        lines = [
            json.dumps({
                "type": "session",
                "version": 3,
                "id": "96ef5f4e-062b-471c-a54f-b7ce0e66f7ee",
                "timestamp": "2026-03-19T12:57:31.615Z",
                "cwd": "/home/bruce/.openclaw/workspace-alice",
            }),
            json.dumps({
                "type": "message",
                "id": "msg-1",
                "timestamp": "2026-03-19T12:57:31.727Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "分析今天的市场"}],
                },
            }),
            json.dumps({
                "type": "message",
                "id": "msg-2",
                "timestamp": "2026-03-19T12:57:35.000Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "好的，让我查看一下"},
                        {"type": "toolCall", "id": "tc1", "name": "exec",
                         "arguments": {"cmd": "fetch-market"}},
                    ],
                },
            }),
        ]
        path = Path(self.tmpdir) / "96ef5f4e-062b-471c-a54f-b7ce0e66f7ee.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, MessageRole.USER)
        self.assertEqual(msgs[0].content, "分析今天的市场")
        self.assertEqual(msgs[0].runtime, Runtime.OPENCLAW)
        self.assertEqual(msgs[1].role, MessageRole.ASSISTANT)
        self.assertEqual(msgs[1].content, "好的，让我查看一下")
        self.assertEqual(len(msgs[1].tool_calls), 1)
        self.assertEqual(msgs[1].tool_calls[0].name, "exec")

    def test_session_id_is_filename_stem(self):
        """OpenClaw session ID 直接是文件名（UUID）。"""
        lines = [
            json.dumps({
                "type": "session",
                "version": 3,
                "id": "abc123",
                "timestamp": "2026-03-19T12:00:00Z",
                "cwd": "/tmp",
            }),
            json.dumps({
                "type": "message",
                "id": "m1",
                "timestamp": "2026-03-19T12:00:01Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "test"}],
                },
            }),
        ]
        path = Path(self.tmpdir) / "my-session-uuid.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(msgs[0].session_id, "my-session-uuid")

    def test_skip_non_message_types(self):
        """跳过 thinking_level_change、custom 等非消息类型。"""
        lines = [
            json.dumps({"type": "thinking_level_change", "id": "x",
                         "timestamp": "2026-03-19T12:00:00Z", "thinkingLevel": "off"}),
            json.dumps({"type": "custom", "customType": "model-snapshot",
                         "data": {}, "id": "y", "timestamp": "2026-03-19T12:00:00Z"}),
            json.dumps({"type": "model_change", "id": "z",
                         "timestamp": "2026-03-19T12:00:00Z"}),
        ]
        path = Path(self.tmpdir) / "test.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 0)

    def test_skip_tool_result_messages(self):
        """toolResult 消息被跳过。"""
        lines = [
            json.dumps({
                "type": "message",
                "id": "tr1",
                "timestamp": "2026-03-19T12:00:00Z",
                "message": {
                    "role": "toolResult",
                    "toolCallId": "tc1",
                    "toolName": "exec",
                    "content": [{"type": "text", "text": "output here"}],
                },
            }),
        ]
        path = Path(self.tmpdir) / "test.jsonl"
        path.write_text("\n".join(lines))

        msgs = self.reader.read_session(path)
        self.assertEqual(len(msgs), 0)

    def test_get_session_info(self):
        """测试 session 元信息提取。"""
        lines = [
            json.dumps({
                "type": "session",
                "version": 3,
                "id": "sess-1",
                "timestamp": "2026-03-19T12:00:00Z",
                "cwd": "/home/bruce/.openclaw/workspace-alice",
            }),
            json.dumps({
                "type": "message",
                "id": "m1",
                "timestamp": "2026-03-19T12:00:01Z",
                "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]},
            }),
            json.dumps({
                "type": "message",
                "id": "m2",
                "timestamp": "2026-03-19T12:05:00Z",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
            }),
        ]
        # 模拟 agent 目录结构
        agent_dir = Path(self.tmpdir) / "agents" / "alice" / "sessions"
        agent_dir.mkdir(parents=True)
        path = agent_dir / "sess-1.jsonl"
        path.write_text("\n".join(lines))

        info = self.reader.get_session_info(path)
        self.assertIsNotNone(info)
        self.assertEqual(info.session_id, "sess-1")
        self.assertEqual(info.runtime, Runtime.OPENCLAW)
        self.assertEqual(info.project_path, "/home/bruce/.openclaw/workspace-alice")
        self.assertEqual(info.message_count, 2)

    def test_extract_agent_name(self):
        """从路径提取 agent 名。"""
        path = Path("/home/bruce/.openclaw/agents/alice/sessions/abc.jsonl")
        self.assertEqual(_extract_agent_name(path), "alice")

        path = Path("/tmp/random/file.jsonl")
        self.assertEqual(_extract_agent_name(path), "unknown")


if __name__ == "__main__":
    unittest.main()
