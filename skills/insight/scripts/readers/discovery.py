"""跨 runtime session 发现。

给定项目路径，自动在 Claude Code / Codex / Pi / OpenClaw 四个 runtime 中
查找该项目的所有 session 文件。
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from ..models import Runtime, SessionInfo
from .claude_reader import ClaudeReader
from .claude_reader import find_project_sessions as find_claude_sessions
from .codex_reader import CodexReader
from .codex_reader import find_project_sessions as find_codex_sessions
from .openclaw_reader import OpenClawReader, find_all_sessions as find_openclaw_sessions
from .pi_reader import PiReader
from .pi_reader import find_project_sessions as find_pi_sessions

logger = logging.getLogger(__name__)


def discover_sessions(
    project_path: str,
    runtimes: list[Runtime] | None = None,
    since: datetime | None = None,
    limit: int = 0,
) -> list[SessionInfo]:
    """发现指定项目在各 runtime 中的所有 session。

    Args:
        project_path: 项目根目录绝对路径。
        runtimes: 要搜索的 runtime 列表，None 表示全部。
        since: 只返回此时间之后的 session。
        limit: 最大返回数量，0 表示不限。

    Returns:
        按时间倒序排列的 SessionInfo 列表。
    """
    if runtimes is None:
        runtimes = [Runtime.CLAUDE, Runtime.CODEX, Runtime.PI, Runtime.OPENCLAW]

    project_path = str(Path(project_path).resolve())
    all_sessions: list[SessionInfo] = []

    if Runtime.CLAUDE in runtimes:
        all_sessions.extend(
            _discover_claude(project_path, since)
        )

    if Runtime.CODEX in runtimes:
        all_sessions.extend(
            _discover_codex(project_path, since)
        )

    if Runtime.PI in runtimes:
        all_sessions.extend(
            _discover_pi(project_path, since)
        )

    if Runtime.OPENCLAW in runtimes:
        all_sessions.extend(
            _discover_openclaw(since)
        )

    # 按开始时间倒序
    all_sessions.sort(key=lambda s: s.start_time, reverse=True)

    if limit > 0:
        all_sessions = all_sessions[:limit]

    logger.info(
        "Discovered %d sessions for %s (runtimes: %s)",
        len(all_sessions),
        project_path,
        [r.value for r in runtimes],
    )
    return all_sessions


def _discover_claude(
    project_path: str, since: datetime | None
) -> list[SessionInfo]:
    """发现 Claude Code session。"""
    reader = ClaudeReader()
    sessions: list[SessionInfo] = []

    for path in find_claude_sessions(project_path):
        if since is not None:
            mtime = datetime.fromtimestamp(
                path.stat().st_mtime, tz=since.tzinfo
            )
            if mtime < since:
                continue
        info = reader.get_session_info(path)
        if info is not None:
            sessions.append(info)

    logger.debug("Found %d Claude Code sessions", len(sessions))
    return sessions


def _discover_codex(
    project_path: str, since: datetime | None
) -> list[SessionInfo]:
    """发现 Codex session。"""
    reader = CodexReader()
    sessions: list[SessionInfo] = []

    for path in find_codex_sessions(project_path, since):
        info = reader.get_session_info(path)
        if info is not None:
            sessions.append(info)

    logger.debug("Found %d Codex sessions", len(sessions))
    return sessions


def _discover_pi(
    project_path: str, since: datetime | None
) -> list[SessionInfo]:
    """发现 Pi session。"""
    reader = PiReader()
    sessions: list[SessionInfo] = []

    for path in find_pi_sessions(project_path, since):
        info = reader.get_session_info(path)
        if info is not None:
            sessions.append(info)

    logger.debug("Found %d Pi sessions", len(sessions))
    return sessions


def _discover_openclaw(
    since: datetime | None,
) -> list[SessionInfo]:
    """发现 OpenClaw session（扫描所有 agent）。"""
    reader = OpenClawReader()
    sessions: list[SessionInfo] = []

    for path in find_openclaw_sessions(since):
        info = reader.get_session_info(path)
        if info is not None:
            sessions.append(info)

    logger.debug("Found %d OpenClaw sessions", len(sessions))
    return sessions
