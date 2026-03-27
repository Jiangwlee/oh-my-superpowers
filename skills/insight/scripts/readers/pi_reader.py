"""Pi Agent 会话解析器。

解析 ~/.pi/agent/sessions/<project-path-encoded>/<timestamp>_<uuid>.jsonl (v3 格式)。

JSONL 行 type 值：
- "session"：会话初始化，version=3, cwd 标识项目
- "message"：用户/助手消息，message.role = user|assistant|toolResult
- "model_change"：模型切换事件（跳过）
- "thinking_level_change"：思考级别变更（跳过）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import MessageRole, Runtime, SessionInfo, ToolCall, UnifiedMessage

logger = logging.getLogger(__name__)

PI_SESSIONS_DIR = Path.home() / ".pi" / "agent" / "sessions"


class PiReader:
    """解析 Pi agent session JSONL 文件 (v3 格式)。"""

    runtime = Runtime.PI

    def read_session(self, file_path: str | Path) -> list[UnifiedMessage]:
        """解析单个 session 文件，返回统一消息列表。"""
        path = Path(file_path)
        if not path.exists():
            logger.warning("Session file not found: %s", path)
            return []

        session_id = _extract_session_id(path.name)
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

        session_id = _extract_session_id(path.name)
        project_path = _decode_project_path(path.parent.name)

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
            runtime=Runtime.PI,
            project_path=project_path,
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
        """解析 Pi v3 message 事件。"""
        message = data.get("message", {})
        content_blocks = message.get("content", [])
        if not isinstance(content_blocks, list):
            # content 可能是纯字符串
            if isinstance(content_blocks, str):
                return UnifiedMessage(
                    role=role,
                    content=content_blocks,
                    timestamp=_parse_timestamp(data.get("timestamp"))
                    or datetime.now(),
                    session_id=session_id,
                    runtime=Runtime.PI,
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
            runtime=Runtime.PI,
            message_id=data.get("id", ""),
            tool_calls=tool_calls,
            raw=data,
        )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _extract_session_id(filename: str) -> str:
    """从文件名提取 session ID。

    2026-03-25T15-09-44-730Z_d1d64fc7-ff63-4c5b-bc76-fdfb5520f91f.jsonl
    → d1d64fc7-ff63-4c5b-bc76-fdfb5520f91f
    """
    stem = Path(filename).stem
    if "_" in stem:
        return stem.split("_", 1)[1]
    return stem


def _decode_project_path(dir_name: str) -> str:
    """从 Pi 目录名解码项目路径。

    --home-bruce-Projects-oh-my-superpowers-- → /home/bruce/Projects/oh-my-superpowers
    """
    if not dir_name:
        return ""
    # 去掉首尾 --，中间 - 替换为 /
    stripped = dir_name.strip("-")
    return "/" + stripped.replace("-", "/")


def _parse_timestamp(ts: str | None) -> datetime | None:
    """解析 ISO 8601 时间戳。"""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def find_project_sessions(
    project_path: str, since: datetime | None = None
) -> list[Path]:
    """查找指定项目的所有 Pi session 文件。

    Pi 用 --<path-encoded>-- 目录名组织，直接匹配目录名。
    """
    if not PI_SESSIONS_DIR.exists():
        return []

    # 将项目路径编码为 Pi 目录名格式
    encoded = "--" + project_path.lstrip("/").replace("/", "-") + "--"
    project_dir = PI_SESSIONS_DIR / encoded

    if not project_dir.exists():
        return []

    sessions: list[Path] = []
    for f in project_dir.iterdir():
        if f.suffix == ".jsonl":
            if since is not None:
                mtime = datetime.fromtimestamp(
                    f.stat().st_mtime, tz=since.tzinfo
                )
                if mtime < since:
                    continue
            sessions.append(f)

    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)
