"""Codex 会话解析器。

解析 ~/.codex/sessions/<year>/<month>/<day>/rollout-<timestamp>-<uuid>.jsonl 格式。

JSONL 行 type 值：
- "session_meta"：会话元数据（首行），payload.cwd 标识项目
- "response_item"：消息容器，payload.role = user|developer|assistant
- "event_msg"：事件通知（task_started, task_complete 等）
- "turn_context"：每轮上下文（模型、策略等）
- "token_count"：token 用量
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import MessageRole, Runtime, SessionInfo, ToolCall, UnifiedMessage

logger = logging.getLogger(__name__)

CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


class CodexReader:
    """解析 Codex session JSONL 文件。"""

    runtime = Runtime.CODEX

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

                if data.get("type") == "session_meta":
                    project_path = data.get("payload", {}).get("cwd", "")
                elif data.get("type") == "response_item":
                    role = data.get("payload", {}).get("role", "")
                    if role in ("user", "assistant"):
                        msg_count += 1

        if first_ts is None:
            return None

        return SessionInfo(
            session_id=session_id,
            runtime=Runtime.CODEX,
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
        if data.get("type") != "response_item":
            return None

        payload = data.get("payload", {})
        role = payload.get("role", "")

        if role == "user":
            return self._parse_message(data, session_id, MessageRole.USER)
        elif role == "assistant":
            return self._parse_message(data, session_id, MessageRole.ASSISTANT)
        # developer 消息（系统提示）→ 跳过
        return None

    def _parse_message(
        self, data: dict[str, Any], session_id: str, role: MessageRole
    ) -> UnifiedMessage | None:
        """解析 response_item 消息。"""
        payload = data.get("payload", {})
        content_blocks = payload.get("content", [])
        if not isinstance(content_blocks, list):
            return None

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type", "")
            if block_type in ("input_text", "output_text", "text"):
                text_parts.append(block.get("text", ""))
            elif block_type == "toolCall":
                tool_calls.append(
                    ToolCall(
                        name=block.get("name", ""),
                        arguments=block.get("arguments", {}),
                        tool_use_id=block.get("id", ""),
                    )
                )
            # reasoning blocks → 跳过

        content = "\n".join(text_parts)
        if not content and not tool_calls:
            return None

        return UnifiedMessage(
            role=role,
            content=content,
            timestamp=_parse_timestamp(data.get("timestamp")) or datetime.now(),
            session_id=session_id,
            runtime=Runtime.CODEX,
            message_id=payload.get("id", ""),
            tool_calls=tool_calls,
            raw=data,
        )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _extract_session_id(filename: str) -> str:
    """从文件名提取 session ID。

    rollout-2026-03-09T21-30-12-019cd2ca-7fe5-75c0-8653-b5d3a7d73eb9.jsonl
    → 019cd2ca-7fe5-75c0-8653-b5d3a7d73eb9
    """
    stem = Path(filename).stem
    # 格式: rollout-<timestamp>-<uuid>
    # UUID 是最后 5 段，用 - 分隔
    parts = stem.split("-")
    if len(parts) >= 5:
        return "-".join(parts[-5:])
    return stem


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
    """查找指定项目的所有 Codex session 文件。

    Codex 按日期组织目录，需要扫描并通过 session_meta 的 cwd 字段匹配项目。
    """
    if not CODEX_SESSIONS_DIR.exists():
        return []

    candidates: list[Path] = []

    # 遍历年/月/日目录
    for jsonl in CODEX_SESSIONS_DIR.rglob("rollout-*.jsonl"):
        # 用文件修改时间做粗过滤
        if since is not None:
            mtime = datetime.fromtimestamp(
                jsonl.stat().st_mtime, tz=since.tzinfo
            )
            if mtime < since:
                continue

        # 读取 session_meta 行检查 cwd
        try:
            with open(jsonl, encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    continue
                data = json.loads(first_line)
                if data.get("type") == "session_meta":
                    cwd = data.get("payload", {}).get("cwd", "")
                    if cwd and _is_same_project(cwd, project_path):
                        candidates.append(jsonl)
        except (json.JSONDecodeError, OSError):
            continue

    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def _is_same_project(cwd: str, project_path: str) -> bool:
    """判断 cwd 是否属于目标项目（精确匹配或子目录）。"""
    cwd = cwd.rstrip("/")
    project_path = project_path.rstrip("/")
    return cwd == project_path or cwd.startswith(project_path + "/")
