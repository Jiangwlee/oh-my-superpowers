"""Claude Code 会话解析器。

解析 ~/.claude/projects/<project-path>/<session-id>.jsonl 格式。

JSONL 行 type 值：
- "user"：用户消息，message.content 为字符串或 content block 数组
- "assistant"：助手消息，message.content 为 content block 数组
- "progress"：工具/hook 执行进度（跳过）
- "file-history-snapshot"：文件追踪快照（跳过）
- "system"：系统/错误事件（跳过）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import MessageRole, Runtime, SessionInfo, ToolCall, UnifiedMessage

logger = logging.getLogger(__name__)

# Claude Code 项目目录前缀
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


class ClaudeReader:
    """解析 Claude Code session JSONL 文件。"""

    runtime = Runtime.CLAUDE

    def read_session(self, file_path: str | Path) -> list[UnifiedMessage]:
        """解析单个 session 文件，返回统一消息列表。"""
        path = Path(file_path)
        if not path.exists():
            logger.warning("Session file not found: %s", path)
            return []

        session_id = path.stem
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
        """获取 session 元信息（不读取全部消息）。"""
        path = Path(file_path)
        if not path.exists():
            return None

        session_id = path.stem
        project_path = _extract_project_path(path.parent.name)

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

                if data.get("type") in ("user", "assistant"):
                    msg_count += 1

        if first_ts is None:
            return None

        return SessionInfo(
            session_id=session_id,
            runtime=Runtime.CLAUDE,
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
        line_type = data.get("type")

        if line_type == "user":
            return self._parse_user(data, session_id)
        elif line_type == "assistant":
            return self._parse_assistant(data, session_id)
        # progress, file-history-snapshot, system → 跳过
        return None

    def _parse_user(
        self, data: dict[str, Any], session_id: str
    ) -> UnifiedMessage | None:
        """解析用户消息。"""
        message = data.get("message", {})
        content = _extract_content(message.get("content", ""))
        if not content:
            return None

        return UnifiedMessage(
            role=MessageRole.USER,
            content=content,
            timestamp=_parse_timestamp(data.get("timestamp")) or datetime.now(),
            session_id=session_id,
            runtime=Runtime.CLAUDE,
            message_id=data.get("uuid", ""),
            raw=data,
        )

    def _parse_assistant(
        self, data: dict[str, Any], session_id: str
    ) -> UnifiedMessage | None:
        """解析助手消息。"""
        message = data.get("message", {})
        content_blocks = message.get("content", [])
        if not isinstance(content_blocks, list):
            return None

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                        tool_use_id=block.get("id", ""),
                    )
                )
            # thinking blocks → 跳过

        content = "\n".join(text_parts)
        if not content and not tool_calls:
            return None

        return UnifiedMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            timestamp=_parse_timestamp(data.get("timestamp")) or datetime.now(),
            session_id=session_id,
            runtime=Runtime.CLAUDE,
            message_id=data.get("uuid", ""),
            tool_calls=tool_calls,
            raw=data,
        )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _extract_content(raw_content: str | list[dict[str, Any]]) -> str:
    """从 Claude Code 的 content 字段提取纯文本。

    content 可以是字符串，也可以是 content block 数组（tool_result 等）。
    """
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts = []
        for block in raw_content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    parts.append(block.get("content", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _extract_project_path(dir_name: str) -> str:
    """从 Claude Code 项目目录名还原项目路径。

    目录名格式：-home-bruce-Projects-oh-my-superpowers → /home/bruce/Projects/oh-my-superpowers
    """
    if not dir_name:
        return ""
    # 将首个 - 替换为 /，其余 - 也替换为 /
    return "/" + dir_name.lstrip("-").replace("-", "/")


def _parse_timestamp(ts: str | None) -> datetime | None:
    """解析 ISO 8601 时间戳。"""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def find_project_sessions(project_path: str) -> list[Path]:
    """查找指定项目的所有 Claude Code session 文件。"""
    # 将项目路径转换为 Claude Code 目录名格式
    dir_name = project_path.replace("/", "-")
    project_dir = CLAUDE_PROJECTS_DIR / dir_name

    if not project_dir.exists():
        return []

    sessions = []
    for f in project_dir.iterdir():
        if f.suffix == ".jsonl" and not f.is_dir():
            sessions.append(f)

    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)
