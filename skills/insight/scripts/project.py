"""项目检测——通过 git remote URL 哈希标识项目。

复用 ECC instinct 的 detect_project 策略：
1. 优先用 git remote get-url origin 的 SHA256[:12]
2. 回退到项目根目录路径的 SHA256[:12]
"""

from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from pathlib import Path

from .models import ProjectInfo

logger = logging.getLogger(__name__)


def detect_project(path: str | Path | None = None) -> ProjectInfo:
    """检测当前项目信息。

    Args:
        path: 项目路径，None 时使用当前目录。

    Returns:
        ProjectInfo，检测失败时返回基于路径的 fallback。
    """
    if path is None:
        path = Path.cwd()
    path = Path(path).resolve()

    # 获取 git 根目录
    project_root = _git_toplevel(path)
    if project_root is None:
        # 不是 git 仓库
        return ProjectInfo(
            id=_hash(str(path)),
            name=path.name,
            root=str(path),
        )

    # 获取 remote URL
    remote_url = _git_remote_url(project_root)

    # 用 remote URL 做 hash（跨机器一致），fallback 用路径
    hash_source = remote_url if remote_url else str(project_root)
    project_id = _hash(hash_source)

    return ProjectInfo(
        id=project_id,
        name=project_root.name,
        root=str(project_root),
        remote=remote_url,
    )


def _git_toplevel(path: Path) -> Path | None:
    """获取 git 仓库根目录。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=path,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _git_remote_url(project_root: Path) -> str:
    """获取 git remote origin URL（去除凭据）。"""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            return _strip_credentials(url)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def _strip_credentials(url: str) -> str:
    """从 URL 中去除凭据信息。"""
    return re.sub(r"://[^@]+@", "://", url)


def _hash(s: str) -> str:
    """SHA256 前 12 字符。"""
    return hashlib.sha256(s.encode()).hexdigest()[:12]
