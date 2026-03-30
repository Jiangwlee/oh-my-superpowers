#!/usr/bin/env python3
"""Skill 使用频率审计脚本。

扫描 Claude Code session JSONL 文件，提取 Skill 和 Agent 工具调用，
输出使用频率统计，用于评估元基础设施的 ROI。

用法：
    python scripts/skill-usage-audit.py [--days 14] [--project <path>]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path


CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class SkillCall:
    """单次 skill 调用记录。"""
    skill: str
    timestamp: datetime
    session_id: str
    project: str
    args: str = ""


@dataclass
class AgentCall:
    """单次 Agent 工具调用记录。"""
    description: str
    subagent_type: str
    timestamp: datetime
    session_id: str
    project: str


@dataclass
class SkillStats:
    """单个 skill 的统计数据。"""
    name: str
    call_count: int = 0
    sessions: set[str] = field(default_factory=set)
    projects: set[str] = field(default_factory=set)
    first_seen: datetime | None = None
    last_seen: datetime | None = None


def parse_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def dir_name_to_project(dir_name: str) -> str:
    """从 Claude Code 项目目录名还原可读项目名。

    -home-bruce-Projects-oh-my-superpowers → oh-my-superpowers
    """
    parts = dir_name.lstrip("-").split("-")
    # 取最后一段有意义的项目名
    # 找 Projects/ 之后的部分，或者直接取最后几段
    try:
        idx = parts.index("Projects")
        return "-".join(parts[idx + 1:])
    except ValueError:
        # 没有 Projects 目录，取最后两段
        return "-".join(parts[-2:]) if len(parts) >= 2 else dir_name


def scan_session(file_path: Path, project: str, cutoff: datetime) -> tuple[list[SkillCall], list[AgentCall]]:
    """扫描单个 session 文件，提取 Skill 和 Agent 调用。"""
    skills: list[SkillCall] = []
    agents: list[AgentCall] = []
    session_id = file_path.stem

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if data.get("type") != "assistant":
                continue

            ts = parse_timestamp(data.get("timestamp"))
            if ts is None or ts < cutoff:
                continue

            message = data.get("message", {})
            content_blocks = message.get("content", [])
            if not isinstance(content_blocks, list):
                continue

            for block in content_blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                if tool_name == "Skill":
                    skill_name = tool_input.get("skill", "unknown")
                    skills.append(SkillCall(
                        skill=skill_name,
                        timestamp=ts,
                        session_id=session_id,
                        project=project,
                        args=tool_input.get("args", ""),
                    ))
                elif tool_name == "Agent":
                    agents.append(AgentCall(
                        description=tool_input.get("description", ""),
                        subagent_type=tool_input.get("subagent_type", "general-purpose"),
                        timestamp=ts,
                        session_id=session_id,
                        project=project,
                    ))

    return skills, agents


def scan_all_sessions(days: int, project_filter: str | None) -> tuple[list[SkillCall], list[AgentCall]]:
    """扫描所有 Claude session 文件。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_skills: list[SkillCall] = []
    all_agents: list[AgentCall] = []

    if not CLAUDE_PROJECTS_DIR.exists():
        print(f"未找到 Claude projects 目录: {CLAUDE_PROJECTS_DIR}")
        return [], []

    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        project_name = dir_name_to_project(project_dir.name)

        if project_filter and project_filter not in project_name:
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            # 快速过滤：文件修改时间在 cutoff 之前的跳过
            if datetime.fromtimestamp(jsonl_file.stat().st_mtime, tz=timezone.utc) < cutoff:
                continue

            skills, agents = scan_session(jsonl_file, project_name, cutoff)
            all_skills.extend(skills)
            all_agents.extend(agents)

    return all_skills, all_agents


def print_skill_report(skills: list[SkillCall], days: int) -> None:
    """输出 Skill 使用报告。"""
    if not skills:
        print(f"\n过去 {days} 天内没有 Skill 调用记录。")
        return

    # 按 skill 名聚合
    stats: dict[str, SkillStats] = {}
    for call in skills:
        if call.skill not in stats:
            stats[call.skill] = SkillStats(name=call.skill)
        s = stats[call.skill]
        s.call_count += 1
        s.sessions.add(call.session_id)
        s.projects.add(call.project)
        if s.first_seen is None or call.timestamp < s.first_seen:
            s.first_seen = call.timestamp
        if s.last_seen is None or call.timestamp > s.last_seen:
            s.last_seen = call.timestamp

    # 按调用次数排序
    sorted_stats = sorted(stats.values(), key=lambda s: s.call_count, reverse=True)

    print(f"\n## Skill 使用频率（过去 {days} 天）\n")
    print(f"{'Skill':<30} {'调用次数':>8} {'Sessions':>8} {'Projects':>8} {'最近使用':<12}")
    print("-" * 78)
    for s in sorted_stats:
        last = s.last_seen.strftime("%m-%d") if s.last_seen else "?"
        print(f"{s.name:<30} {s.call_count:>8} {len(s.sessions):>8} {len(s.projects):>8} {last:<12}")

    print(f"\n总计: {len(skills)} 次调用, {len(stats)} 个不同 Skill")


def print_agent_report(agents: list[AgentCall], days: int) -> None:
    """输出 Agent 工具使用报告。"""
    if not agents:
        print(f"\n过去 {days} 天内没有 Agent 工具调用记录。")
        return

    # 按 subagent_type 聚合
    type_counts: dict[str, int] = defaultdict(int)
    type_sessions: dict[str, set[str]] = defaultdict(set)
    for call in agents:
        type_counts[call.subagent_type] += 1
        type_sessions[call.subagent_type].add(call.session_id)

    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

    print(f"\n## Agent 子类型使用频率（过去 {days} 天）\n")
    print(f"{'SubAgent Type':<30} {'调用次数':>8} {'Sessions':>8}")
    print("-" * 50)
    for agent_type, count in sorted_types:
        sessions = len(type_sessions[agent_type])
        print(f"{agent_type:<30} {count:>8} {sessions:>8}")

    print(f"\n总计: {len(agents)} 次 Agent 调用")


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill 使用频率审计")
    parser.add_argument("--days", type=int, default=14, help="扫描最近 N 天（默认 14）")
    parser.add_argument("--project", type=str, default=None, help="只扫描包含此关键词的项目")
    args = parser.parse_args()

    print(f"扫描 Claude sessions（最近 {args.days} 天）...")
    if args.project:
        print(f"项目过滤: {args.project}")

    skills, agents = scan_all_sessions(args.days, args.project)
    print_skill_report(skills, args.days)
    print_agent_report(agents, args.days)


if __name__ == "__main__":
    main()
