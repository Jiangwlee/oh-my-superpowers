"""Insight skill 数据模型。

定义三层架构的核心数据结构：
- Session 层：UnifiedMessage（统一多 runtime 消息格式）
- Memory 层：CorrectionTrajectory（纠正轨迹）
- Insight 层：Insight（跨会话行为差分）
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Runtime(str, Enum):
    """支持的 AI runtime。"""

    CLAUDE = "claude"
    CODEX = "codex"
    PI = "pi"


class MessageRole(str, Enum):
    """消息角色。"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_RESULT = "tool_result"


class InsightScope(str, Enum):
    """Insight 作用域。"""

    PROJECT = "project"
    USER = "user"


# ---------------------------------------------------------------------------
# Session 层
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    """工具调用记录。"""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str = ""
    output: str | None = None
    is_error: bool = False


@dataclass
class UnifiedMessage:
    """统一消息格式——三个 runtime 的公共抽象。

    从 Claude Code / Codex / Pi 的 JSONL 解析后统一为此格式，
    供下游纠正模式识别和 insight 提取使用。
    """

    role: MessageRole
    content: str
    timestamp: datetime
    session_id: str
    runtime: Runtime
    message_id: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_user(self) -> bool:
        return self.role == MessageRole.USER

    @property
    def is_assistant(self) -> bool:
        return self.role == MessageRole.ASSISTANT


@dataclass
class SessionInfo:
    """会话元信息。"""

    session_id: str
    runtime: Runtime
    project_path: str
    start_time: datetime
    end_time: datetime | None = None
    message_count: int = 0
    file_path: str = ""


# ---------------------------------------------------------------------------
# Memory 层
# ---------------------------------------------------------------------------


@dataclass
class CorrectionExample:
    """单次纠正的上下文快照。"""

    session_id: str
    before: str  # 助手的错误行为
    after: str  # 纠正后的正确行为
    context: str  # 触发纠正的上下文
    user_feedback: str = ""  # 用户的原始纠正话语


@dataclass
class CorrectionTrajectory:
    """纠正轨迹——用户多次纠正→最终收敛的完整路径。

    这是从 Session 到 Insight 的中间产物。
    """

    trigger: str  # 什么情况下触发了错误
    wrong_behavior: str  # 助手的错误默认行为
    corrected_behavior: str  # 最终正确的行为
    messages: list[UnifiedMessage] = field(default_factory=list)
    correction_count: int = 1
    session_id: str = ""
    runtime: Runtime = Runtime.CLAUDE


# ---------------------------------------------------------------------------
# Insight 层
# ---------------------------------------------------------------------------


@dataclass
class Insight:
    """跨会话行为差分——系统的核心价值单元。

    Schema 来自圆桌讨论融合版：behavioral delta 为核心，
    记录 trigger → wrong_default → corrected_behavior 的 diff。
    """

    id: str
    trigger: str
    wrong_default: str
    corrected_behavior: str
    examples: list[CorrectionExample] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    correction_count: int = 1
    confidence: float = 0.5
    first_seen: datetime = field(default_factory=datetime.now)
    last_confirmed: datetime = field(default_factory=datetime.now)
    scope: InsightScope = InsightScope.PROJECT
    why: str = ""
    source_session_ids: list[str] = field(default_factory=list)
    reframes: list[str] = field(default_factory=list)  # memory_ids

    @staticmethod
    def generate_id(trigger: str, wrong_default: str) -> str:
        """基于内容生成稳定 ID（SHA256 前 12 位）。"""
        content = f"{trigger}::{wrong_default}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def to_markdown(self) -> str:
        """序列化为 YAML frontmatter + markdown 格式（QMD 索引用）。"""
        lines = [
            "---",
            f"id: {self.id}",
            f"trigger: {_yaml_quote(self.trigger)}",
            f"wrong_default: {_yaml_quote(self.wrong_default)}",
            f"corrected_behavior: {_yaml_quote(self.corrected_behavior)}",
            f"tags: {json.dumps(self.tags, ensure_ascii=False)}",
            f"correction_count: {self.correction_count}",
            f"confidence: {self.confidence}",
            f"first_seen: {self.first_seen.isoformat()}",
            f"last_confirmed: {self.last_confirmed.isoformat()}",
            f"scope: {self.scope.value}",
            f"source_session_ids: {json.dumps(self.source_session_ids)}",
            "---",
            "",
            f"# {self.trigger}",
            "",
            "## Wrong Default",
            "",
            self.wrong_default,
            "",
            "## Corrected Behavior",
            "",
            self.corrected_behavior,
            "",
        ]

        if self.why:
            lines.extend(["## Why", "", self.why, ""])

        if self.examples:
            lines.append("## Examples")
            lines.append("")
            for i, ex in enumerate(self.examples, 1):
                lines.append(f"### Example {i} (session: {ex.session_id})")
                lines.append("")
                lines.append(f"**Before:** {ex.before}")
                lines.append("")
                lines.append(f"**After:** {ex.after}")
                lines.append("")
                if ex.context:
                    lines.append(f"**Context:** {ex.context}")
                    lines.append("")

        return "\n".join(lines)

    @classmethod
    def from_frontmatter(cls, text: str) -> Insight:
        """从 YAML frontmatter + markdown 反序列化。"""
        if not text.startswith("---"):
            raise ValueError("Invalid insight markdown: missing frontmatter")

        end = text.index("---", 3)
        frontmatter = text[3:end].strip()

        data: dict[str, Any] = {}
        for line in frontmatter.split("\n"):
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # 去掉 YAML 引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('\\"', '"')
            data[key] = value

        # 解析 JSON 数组字段
        for arr_field in ("tags", "source_session_ids"):
            if arr_field in data and isinstance(data[arr_field], str):
                try:
                    data[arr_field] = json.loads(data[arr_field])
                except json.JSONDecodeError:
                    data[arr_field] = []

        return cls(
            id=data.get("id", ""),
            trigger=data.get("trigger", ""),
            wrong_default=data.get("wrong_default", ""),
            corrected_behavior=data.get("corrected_behavior", ""),
            tags=data.get("tags", []),
            correction_count=int(data.get("correction_count", 1)),
            confidence=float(data.get("confidence", 0.5)),
            first_seen=_parse_datetime(data.get("first_seen", "")),
            last_confirmed=_parse_datetime(data.get("last_confirmed", "")),
            scope=InsightScope(data.get("scope", "project")),
            source_session_ids=data.get("source_session_ids", []),
            # examples 和 reframes 不在 frontmatter 中完整存储
        )


# ---------------------------------------------------------------------------
# 项目检测
# ---------------------------------------------------------------------------


@dataclass
class ProjectInfo:
    """项目标识信息。"""

    id: str  # SHA256[:12] of git remote URL
    name: str  # 目录名
    root: str  # 项目根目录绝对路径
    remote: str = ""  # git remote URL


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _yaml_quote(s: str) -> str:
    """安全 YAML 字符串引用。"""
    if not s:
        return '""'
    # 包含特殊字符时用双引号包裹
    if any(c in s for c in ':{}\n"\'[]&*?|>!%@`'):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return f'"{s}"'


def _parse_datetime(s: str) -> datetime:
    """解析 ISO 8601 日期字符串。"""
    if not s:
        return datetime.now()
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.now()
