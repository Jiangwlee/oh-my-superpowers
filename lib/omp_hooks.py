"""Skill hooks 安装/卸载逻辑。

安全写入流程：backup -> tmp -> edit -> verify -> copy back。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


def install_hooks(
    hooks_json: Path,
    skill_name: str,
    settings_path: Path | None = None,
) -> None:
    """将 skill 的 hooks.json 合并到 Claude Code settings.json。

    Args:
        hooks_json: skill 的 hooks.json 文件路径。
        skill_name: skill 名称，用于 _omp_skill 标记。
        settings_path: settings.json 路径，默认 ~/.claude/settings.json。

    Raises:
        json.JSONDecodeError: hooks.json 格式错误。
        ValueError: hooks.json 缺少 hooks 字段。
    """
    settings_path = settings_path or CLAUDE_SETTINGS

    # 1. 读取 skill 的 hooks.json
    skill_hooks = json.loads(hooks_json.read_text(encoding="utf-8"))
    if "hooks" not in skill_hooks:
        raise ValueError(f"hooks.json missing 'hooks' field: {hooks_json}")

    # 2. 读取现有 settings.json
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        # backup
        bak_path = settings_path.parent / (settings_path.name + ".bak")
        shutil.copy2(settings_path, bak_path)
    else:
        settings = {}
        settings_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. 合并
    if "hooks" not in settings:
        settings["hooks"] = {}

    for event, hook_groups in skill_hooks["hooks"].items():
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        # 去重：移除同 skill 的旧条目
        settings["hooks"][event] = [
            h for h in settings["hooks"][event]
            if h.get("_omp_skill") != skill_name
        ]

        # 追加新条目，附带 _omp_skill 标记
        for group in hook_groups:
            tagged = dict(group)
            tagged["_omp_skill"] = skill_name
            settings["hooks"][event].append(tagged)

    # 4. 安全写入：tmp -> verify -> copy back
    tmp_path = settings_path.parent / (settings_path.name + ".tmp")
    tmp_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # verify
    json.loads(tmp_path.read_text(encoding="utf-8"))

    # atomic replace
    os.replace(str(tmp_path), str(settings_path))


def remove_hooks(
    skill_name: str,
    settings_path: Path | None = None,
) -> None:
    """从 settings.json 中移除指定 skill 的所有 hooks。

    Args:
        skill_name: skill 名称。
        settings_path: settings.json 路径，默认 ~/.claude/settings.json。
    """
    settings_path = settings_path or CLAUDE_SETTINGS

    if not settings_path.exists():
        return

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {})
    if not hooks:
        return

    # 移除目标 skill 的条目
    empty_events: list[str] = []
    for event, hook_groups in hooks.items():
        hooks[event] = [
            h for h in hook_groups
            if h.get("_omp_skill") != skill_name
        ]
        if not hooks[event]:
            empty_events.append(event)

    # 清理空数组
    for event in empty_events:
        del hooks[event]

    if not hooks:
        del settings["hooks"]

    # 写回
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
