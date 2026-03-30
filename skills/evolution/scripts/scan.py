#!/usr/bin/env python3
"""Evolution scan — 增量扫描 session 数据，输出机械信号和 session 样本。

用法：
    scan.py [--source <dir>] [--days <n>] [--project-root <dir>]

输出 JSON 到 stdout，同时写入 last-scan.json。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# --- 常量 ---

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
EVOLUTION_DATA_DIR = Path(
    os.environ.get(
        "EVOLUTION_DATA_DIR",
        str(Path.home() / ".local" / "share" / "oh-my-superpowers" / "evolution"),
    )
)
STATE_FILE = EVOLUTION_DATA_DIR / "state.json"


# --- 数据结构 ---


@dataclass
class MechanicalSignal:
    """一条机械信号。"""

    skill: str
    signal: str
    value: str


@dataclass
class SessionSample:
    """一条 session 样本片段。"""

    skill: str
    session_id: str
    project: str
    file: str
    timestamp: str
    user_message_before: str = ""
    user_message_after: str = ""


@dataclass
class ScanResult:
    """扫描结果。"""

    scan_time: str
    project: str
    days: int
    sessions_scanned: int
    mechanical: list[MechanicalSignal] = field(default_factory=list)
    session_samples: list[SessionSample] = field(default_factory=list)
    skill_usage: dict[str, int] = field(default_factory=dict)


# --- 状态管理 ---


def load_state() -> dict:
    """加载全局扫描状态。"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"cursors": {}}


def save_state(state: dict) -> None:
    """保存全局扫描状态。"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_project_data_dir(project_name: str) -> Path:
    """获取项目级数据目录。"""
    d = EVOLUTION_DATA_DIR / "projects" / project_name
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- Session 扫描 ---


def find_session_files(source_dir: Path, days: int) -> list[tuple[str, Path]]:
    """查找 source_dir 下所有项目的 Claude session 文件。

    Returns:
        [(project_name, file_path), ...]
    """
    cutoff_mtime = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    results: list[tuple[str, Path]] = []

    if not CLAUDE_PROJECTS_DIR.exists():
        return results

    # 构建 source_dir 下项目路径的编码集合，用于过滤
    source_projects: set[str] = set()
    if source_dir.exists():
        for child in source_dir.iterdir():
            if child.is_dir():
                # 编码路径格式：/home/bruce/Projects/foo → -home-bruce-Projects-foo
                encoded = str(child.resolve()).replace("/", "-")
                source_projects.add(encoded)

    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # 过滤：只保留 source_dir 下的项目
        if source_projects:
            dir_name = project_dir.name
            matched = any(dir_name.startswith(sp) for sp in source_projects)
            if not matched:
                continue

        project_name = _dir_name_to_project(project_dir.name)

        for jsonl_file in project_dir.glob("*.jsonl"):
            if jsonl_file.stat().st_mtime < cutoff_mtime:
                continue
            results.append((project_name, jsonl_file))

    return results


def scan_session(
    file_path: Path,
    project: str,
    target_skills: set[str],
) -> tuple[dict[str, int], list[SessionSample]]:
    """扫描单个 session，提取 skill 调用数据和上下文。

    Returns:
        (usage_counts, samples)
    """
    usage: dict[str, int] = {}
    samples: list[SessionSample] = []
    session_id = file_path.stem

    lines_data: list[dict] = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines_data.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # 提取所有 user 和 assistant 消息，按顺序
    last_user_content = ""

    for i, data in enumerate(lines_data):
        line_type = data.get("type")

        if line_type == "user":
            content = _extract_text_content(data.get("message", {}).get("content", ""))
            if content:
                last_user_content = content[:500]  # 截断，节省 token

        elif line_type == "assistant":
            message = data.get("message", {})
            content_blocks = message.get("content", [])
            if not isinstance(content_blocks, list):
                continue

            ts = data.get("timestamp", "")

            for block in content_blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                if tool_name != "Skill":
                    continue

                skill_name = tool_input.get("skill", "")
                if not skill_name:
                    continue

                # 统计使用量（全部 skill，不只是 target）
                usage[skill_name] = usage.get(skill_name, 0) + 1

                # 只对 target skills 提取样本
                if skill_name not in target_skills:
                    continue

                # 找到下一条 user 消息作为 after context
                next_user = ""
                for j in range(i + 1, min(i + 10, len(lines_data))):
                    if lines_data[j].get("type") == "user":
                        next_msg = lines_data[j].get("message", {})
                        next_user = _extract_text_content(
                            next_msg.get("content", "")
                        )[:500]
                        break

                samples.append(
                    SessionSample(
                        skill=skill_name,
                        session_id=session_id,
                        project=project,
                        file=str(file_path),
                        timestamp=ts,
                        user_message_before=last_user_content,
                        user_message_after=next_user,
                    )
                )

    return usage, samples


# --- 机械信号检测 ---


def detect_mechanical_signals(
    project_root: Path,
    skill_usage: dict[str, int],
    target_skills: set[str],
    days: int,
    memory_dir: Path | None,
) -> list[MechanicalSignal]:
    """检测机械信号。"""
    signals: list[MechanicalSignal] = []

    for skill_name in sorted(target_skills):
        skill_dir = project_root / "skills" / skill_name
        skill_md = skill_dir / "SKILL.md"

        # 使用频率
        count = skill_usage.get(skill_name, 0)
        if count == 0:
            signals.append(
                MechanicalSignal(skill_name, "zero_usage", f"0 calls / {days} days")
            )
        elif count <= 2:
            signals.append(
                MechanicalSignal(
                    skill_name, "low_usage", f"{count} calls / {days} days"
                )
            )
        elif count >= 10:
            signals.append(
                MechanicalSignal(
                    skill_name, "high_usage", f"{count} calls / {days} days"
                )
            )

        # SKILL.md 行数
        if skill_md.exists():
            line_count = len(skill_md.read_text(encoding="utf-8").splitlines())
            if line_count > 500:
                signals.append(
                    MechanicalSignal(
                        skill_name, "skill_md_too_long", f"{line_count} lines"
                    )
                )

    # Feedback 检测（从 memory 目录）
    if memory_dir and memory_dir.exists():
        feedback_counts = _count_feedback(memory_dir, target_skills)
        for skill_name, count in feedback_counts.items():
            if count > 0:
                signals.append(
                    MechanicalSignal(
                        skill_name, "has_feedback", f"{count} feedback records"
                    )
                )

    return signals


def _count_feedback(memory_dir: Path, target_skills: set[str]) -> dict[str, int]:
    """从 memory 目录中统计各 skill 的 feedback 数量。"""
    counts: dict[str, int] = {s: 0 for s in target_skills}

    for md_file in memory_dir.glob("*.md"):
        if md_file.name == "MEMORY.md":
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        # 检查是否是 feedback 类型
        is_feedback = False
        if "type: feedback" in content:
            is_feedback = True
        elif "[correction]" in content.lower() or "[feedback]" in content.lower():
            is_feedback = True

        if not is_feedback:
            continue

        # 匹配 skill 名
        content_lower = content.lower()
        for skill_name in target_skills:
            if skill_name.replace("-", " ") in content_lower or skill_name in content_lower:
                counts[skill_name] += 1

    return counts


# --- CLAUDE.md 分析信号 ---


def detect_claude_md_signals(project_root: Path) -> list[MechanicalSignal]:
    """检测 CLAUDE.md 的机械信号。"""
    signals: list[MechanicalSignal] = []
    claude_md = project_root / "CLAUDE.md"

    if not claude_md.exists():
        return signals

    content = claude_md.read_text(encoding="utf-8")
    line_count = len(content.splitlines())

    if line_count > 300:
        signals.append(
            MechanicalSignal("CLAUDE.md", "file_too_long", f"{line_count} lines")
        )

    return signals


# --- 工具函数 ---


def _extract_text_content(raw_content: str | list | dict) -> str:
    """从 Claude 的 content 字段提取纯文本。"""
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts = []
        for block in raw_content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _dir_name_to_project(dir_name: str) -> str:
    """从 Claude 项目目录名提取可读项目名。"""
    parts = dir_name.lstrip("-").split("-")
    try:
        idx = parts.index("Projects")
        return "-".join(parts[idx + 1 :])
    except ValueError:
        return "-".join(parts[-2:]) if len(parts) >= 2 else dir_name


def _detect_project_root() -> Path:
    """检测当前项目根目录。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return Path.cwd()


def _find_memory_dir(project_root: Path) -> Path | None:
    """查找项目对应的 memory 目录。"""
    # Claude Code memory 目录
    encoded = str(project_root.resolve()).replace("/", "-")
    memory_dir = CLAUDE_PROJECTS_DIR / encoded / "memory"
    if memory_dir.exists():
        return memory_dir
    return None


def _discover_target_skills(project_root: Path) -> set[str]:
    """发现当前项目 skills/ 目录下的所有 skill 名。"""
    skills_dir = project_root / "skills"
    if not skills_dir.exists():
        return set()

    result = set()
    for child in skills_dir.iterdir():
        if child.is_dir() and (child / "SKILL.md").exists():
            result.add(child.name)
    return result


# --- 主逻辑 ---


def main() -> None:
    parser = argparse.ArgumentParser(description="Evolution scan")
    parser.add_argument(
        "--source",
        type=str,
        default=str(Path.home() / "Projects"),
        help="扫描哪个目录下的项目 session（默认 ~/Projects）",
    )
    parser.add_argument(
        "--days", type=int, default=30, help="扫描最近 N 天（默认 30）"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="当前项目根目录（默认自动检测）",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else _detect_project_root()
    project_name = project_root.name
    source_dir = Path(args.source)

    # 发现目标 skills
    target_skills = _discover_target_skills(project_root)
    if not target_skills:
        print(
            json.dumps(
                {"error": f"No skills found in {project_root}/skills/"},
                ensure_ascii=False,
            )
        )
        return

    # 加载状态
    state = load_state()
    cursor_key = str(project_root)
    cursor_data = state.get("cursors", {}).get(cursor_key, {})
    # 累计使用计数（跨增量扫描持久化）
    cumulative_usage: dict[str, int] = dict(cursor_data.get("skill_usage", {}))
    # 如果有已扫描 session 但无累计计数，说明是旧版 state → 强制全量重扫
    old_sessions = cursor_data.get("scanned_sessions", [])
    if old_sessions and not cumulative_usage:
        scanned_sessions: set[str] = set()  # 重置游标，全量重扫
    else:
        scanned_sessions = set(old_sessions)

    # 扫描 session 文件
    session_files = find_session_files(source_dir, args.days)

    new_usage: dict[str, int] = {}
    all_samples: list[SessionSample] = []
    new_session_ids: list[str] = []
    sessions_scanned = 0

    for project, file_path in session_files:
        session_id = file_path.stem
        if session_id in scanned_sessions:
            continue

        usage, samples = scan_session(file_path, project, target_skills)

        for skill, count in usage.items():
            new_usage[skill] = new_usage.get(skill, 0) + count
        all_samples.extend(samples)
        new_session_ids.append(session_id)
        sessions_scanned += 1

    # 合并累计使用计数
    for skill, count in new_usage.items():
        cumulative_usage[skill] = cumulative_usage.get(skill, 0) + count

    # 检测机械信号（基于累计数据，不是仅新增数据）
    memory_dir = _find_memory_dir(project_root)
    mechanical = detect_mechanical_signals(
        project_root, cumulative_usage, target_skills, args.days, memory_dir
    )
    mechanical.extend(detect_claude_md_signals(project_root))

    # 构建结果
    result = ScanResult(
        scan_time=datetime.now(timezone.utc).isoformat(),
        project=project_name,
        days=args.days,
        sessions_scanned=sessions_scanned,
        mechanical=mechanical,
        session_samples=all_samples,
        skill_usage={k: v for k, v in sorted(cumulative_usage.items(), key=lambda x: -x[1])},
    )

    # 序列化
    result_dict = {
        "scan_time": result.scan_time,
        "project": result.project,
        "days": result.days,
        "sessions_scanned": result.sessions_scanned,
        "mechanical": [asdict(s) for s in result.mechanical],
        "session_samples": [asdict(s) for s in result.session_samples],
        "skill_usage": result.skill_usage,
    }
    output = json.dumps(result_dict, indent=2, ensure_ascii=False)

    # 输出到 stdout
    print(output)

    # 写入 last-scan.json
    project_data_dir = get_project_data_dir(project_name)
    (project_data_dir / "last-scan.json").write_text(output, encoding="utf-8")

    # 更新状态（含累计使用计数）
    if cursor_key not in state.get("cursors", {}):
        state.setdefault("cursors", {})[cursor_key] = {"scanned_sessions": []}
    state["cursors"][cursor_key]["last_scan_time"] = result.scan_time
    state["cursors"][cursor_key]["scanned_sessions"].extend(new_session_ids)
    state["cursors"][cursor_key]["skill_usage"] = cumulative_usage
    save_state(state)

    # 输出摘要到 stderr
    import sys

    print(
        f"\n扫描完成：{sessions_scanned} 个新 session，"
        f"{len(mechanical)} 条机械信号，"
        f"{len(all_samples)} 条 session 样本",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
