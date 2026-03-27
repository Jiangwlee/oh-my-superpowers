"""OpenClaw 会话解析器。

解析 ~/.openclaw/agents/<agent-name>/sessions/<uuid>.jsonl (v3 格式)。

OpenClaw 底层基于 Pi，JSONL 格式与 Pi v3 完全一致：
- "session"：会话初始化，version=3, cwd 标识工作目录
- "message"：用户/助手消息，message.role = user|assistant|toolResult
- "model_change"：模型切换事件（跳过）
- "thinking_level_change"：思考级别变更（跳过）
- "custom"：自定义事件如 model-snapshot（跳过）

区别在于存储组织方式：
- 按 agent 名分目录，每个 agent = 一个 project
- session 文件名直接是 UUID（无时间戳前缀）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import MessageRole, Runtime, SessionInfo, ToolCall, UnifiedMessage

logger = logging.getLogger(__name__)

OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"


class OpenClawReader:
    """解析 OpenClaw session JSONL 文件。

    底层格式与 Pi v3 一致，解析逻辑相同。
    """

    runtime = Runtime.OPENCLAW

    def read_session(self, file_path: str | Path) -> list[UnifiedMessage]:
        """解析单个 session 文件，返回统一消息列表。"""
        path = Path(file_path)
        if not path.exists():
            logger.warning("Session file not found: %s", path)
            return []

        session_id = path.stem  # UUID 即文件名
        messages: list[UnifiedMessage] = []

        with open(path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed JSON at line %d", line_num)
                    continue

                msg = self._parse_line(data, session_id)
                if msg is not None:
                    messages.append(msg)

        return messages

    def get_session_info(self, file_path: str | Path) -> SessionInfo | None:
        """获取 session 元信息。"""
        path = Path(file_path)
        if not path.exists():
            return None

        session_id = path.stem
        # agent 名从路径推断：.../agents/<agent>/sessions/<uuid>.jsonl
        agent_name = _extract_agent_name(path)
        project_path = ""

        first_ts: datetime | None = None
        last_ts: datetime | None = None
        msg_count = 0

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = _parse_timestamp(data.get("timestamp"))
                if ts is None:
                    continue

                if first_ts is None:
                    first_ts = ts
                last_ts = ts

                if data.get("type") == "session":
                    cwd = data.get("cwd", "")
                    if cwd:
                        project_path = cwd

                if data.get("type") == "message":
                    role = data.get("message", {}).get("role", "")
                    if role in ("user", "assistant"):
                        msg_count += 1

        if first_ts is None:
            return None

        return SessionInfo(
            session_id=session_id,
            runtime=Runtime.OPENCLAW,
            project_path=project_path or f"openclaw:{agent_name}",
            start_time=first_ts,
            end_time=last_ts,
            message_count=msg_count,
            file_path=str(path),
        )

    def _parse_line(
        self, data: dict[str, Any], session_id: str
    ) -> UnifiedMessage | None:
        """解析单行 JSONL。"""
        if data.get("type") != "message":
            return None

        message = data.get("message", {})
        role = message.get("role", "")

        if role == "user":
            return self._parse_message(data, session_id, MessageRole.USER)
        elif role == "assistant":
            return self._parse_message(data, session_id, MessageRole.ASSISTANT)
        # toolResult → 跳过（tool 输出，不是对话）
        return None

    def _parse_message(
        self, data: dict[str, Any], session_id: str, role: MessageRole
    ) -> UnifiedMessage | None:
        """解析 v3 message 事件。"""
        message = data.get("message", {})
        content_blocks = message.get("content", [])
        if not isinstance(content_blocks, list):
            if isinstance(content_blocks, str):
                return UnifiedMessage(
                    role=role,
                    content=content_blocks,
                    timestamp=_parse_timestamp(data.get("timestamp"))
                    or datetime.now(),
                    session_id=session_id,
                    runtime=Runtime.OPENCLAW,
                    message_id=data.get("id", ""),
                    raw=data,
                )
            return None

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "toolCall":
                tool_calls.append(
                    ToolCall(
                        name=block.get("name", ""),
                        arguments=block.get("arguments", {}),
                        tool_use_id=block.get("id", ""),
                    )
                )
            # thinking blocks → 跳过

        content = "\n".join(text_parts)
        if not content and not tool_calls:
            return None

        return UnifiedMessage(
            role=role,
            content=content,
            timestamp=_parse_timestamp(data.get("timestamp")) or datetime.now(),
            session_id=session_id,
            runtime=Runtime.OPENCLAW,
            message_id=data.get("id", ""),
            tool_calls=tool_calls,
            raw=data,
        )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _extract_agent_name(session_path: Path) -> str:
    """从 session 文件路径提取 agent 名。

    ~/.openclaw/agents/alice/sessions/xxx.jsonl → alice
    """
    # sessions 目录的父级就是 agent 目录
    if session_path.parent.name == "sessions":
        return session_path.parent.parent.name
    return "unknown"


def _parse_timestamp(ts: str | None) -> datetime | None:
    """解析 ISO 8601 时间戳。"""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def list_agents() -> list[str]:
    """列出所有 OpenClaw agent 名。"""
    if not OPENCLAW_AGENTS_DIR.exists():
        return []
    return [
        d.name
        for d in OPENCLAW_AGENTS_DIR.iterdir()
        if d.is_dir() and (d / "sessions").is_dir()
    ]


def find_agent_sessions(
    agent_name: str, since: datetime | None = None
) -> list[Path]:
    """查找指定 agent 的所有 session 文件。"""
    sessions_dir = OPENCLAW_AGENTS_DIR / agent_name / "sessions"
    if not sessions_dir.exists():
        return []

    sessions: list[Path] = []
    for f in sessions_dir.iterdir():
        if f.suffix == ".jsonl":
            if since is not None:
                mtime = datetime.fromtimestamp(
                    f.stat().st_mtime, tz=since.tzinfo
                )
                if mtime < since:
                    continue
            sessions.append(f)

    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)


def find_all_sessions(since: datetime | None = None) -> list[Path]:
    """查找所有 agent 的所有 session 文件。"""
    all_sessions: list[Path] = []
    for agent in list_agents():
        all_sessions.extend(find_agent_sessions(agent, since))
    return all_sessions
