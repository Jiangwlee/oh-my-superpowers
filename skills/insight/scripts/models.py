"""Insight skill 数据模型。

定义三层架构的核心数据结构：
- Session 层：UnifiedMessage（统一多 runtime 消息格式）
- Memory 层：Memory（被动记录的事实）
- Insight 层：Insight（主动提炼的模式）
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Runtime(str, Enum):
    """支持的 AI runtime。"""

    CLAUDE = "claude"
    CODEX = "codex"
    PI = "pi"
    OPENCLAW = "openclaw"


class MessageRole(str, Enum):
    """消息角色。"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_RESULT = "tool_result"


class MemoryKind(str, Enum):
    """Memory 的最小可计算分类。"""

    BUG = "bug"
    DECISION = "decision"
    PATTERN = "pattern"
    FRICTION = "friction"
    WORKFLOW = "workflow"
    OTHER = "other"


class Scope(str, Enum):
    """影响范围。"""

    FILE = "file"
    MODULE = "module"
    SKILL = "skill"
    AGENT = "agent"
    PROJECT = "project"
    OTHER = "other"


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
class Memory:
    """一条记忆。被动记录的事实，创建后不可变。

    v3 六字段结构化：kind/scope/summary/source/evidence_ref/confidence。
    """

    id: str  # mem_{hex_timestamp}_{random8}
    kind: MemoryKind
    summary: str  # 人类可读短文本（≤100字）
    scope: Scope
    source: str  # "session_id@runtime"
    evidence_ref: str  # 原始证据位置
    created_at: datetime
    hit_count: int = 0
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """序列化为 YAML frontmatter markdown 格式。"""
        lines = [
            "---",
            f"id: {self.id}",
            f"kind: {self.kind.value}",
            f"summary: {_yaml_quote(self.summary)}",
            f"scope: {self.scope.value}",
            f"source: {_yaml_quote(self.source)}",
            f"evidence_ref: {_yaml_quote(self.evidence_ref)}",
            f"created_at: {_yaml_quote(self.created_at.isoformat())}",
            f"hit_count: {self.hit_count}",
            f"confidence: {self.confidence}",
            f"tags: {json.dumps(self.tags, ensure_ascii=False)}",
            "---",
            "",
        ]
        return "\n".join(lines)

    @classmethod
    def from_frontmatter(cls, text: str) -> Memory:
        """从 YAML frontmatter markdown 反序列化。"""
        data = _parse_frontmatter(text, "memory")

        # 解析 JSON 数组字段
        if "tags" in data and isinstance(data["tags"], str):
            try:
                data["tags"] = json.loads(data["tags"])
            except json.JSONDecodeError:
                data["tags"] = []

        return cls(
            id=data.get("id", ""),
            kind=_parse_enum(MemoryKind, data.get("kind", "other"), MemoryKind.OTHER),
            summary=data.get("summary", ""),
            scope=_parse_enum(Scope, data.get("scope", "project"), Scope.PROJECT),
            source=data.get("source", ""),
            evidence_ref=data.get("evidence_ref", ""),
            created_at=_parse_datetime(data.get("created_at", "")),
            hit_count=int(data.get("hit_count", 0)),
            confidence=float(data.get("confidence", 0.5)),
            tags=data.get("tags", []),
        )


# ---------------------------------------------------------------------------
# Insight 层
# ---------------------------------------------------------------------------


@dataclass
class Insight:
    """一条洞察。主动提炼的模式。"""

    id: str  # ins_{hex_timestamp}_{random4}
    pattern: str  # 一句话描述模式
    action: str  # Agent 应该怎么做
    evidence: list[str]  # 关联的 memory IDs
    scope: Scope
    created_at: datetime
    last_validated_at: datetime
    evidence_count: int = 0
    confidence: float = 0.6
    tags: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """序列化为 YAML frontmatter markdown 格式。"""
        lines = [
            "---",
            f"id: {self.id}",
            f"pattern: {_yaml_quote(self.pattern)}",
            f"action: {_yaml_quote(self.action)}",
            f"evidence: {json.dumps(self.evidence, ensure_ascii=False)}",
            f"scope: {self.scope.value}",
            f"created_at: {_yaml_quote(self.created_at.isoformat())}",
            f"last_validated_at: {_yaml_quote(self.last_validated_at.isoformat())}",
            f"evidence_count: {self.evidence_count}",
            f"confidence: {self.confidence}",
            f"tags: {json.dumps(self.tags, ensure_ascii=False)}",
            "---",
            "",
        ]
        return "\n".join(lines)

    @classmethod
    def from_frontmatter(cls, text: str) -> Insight:
        """从 YAML frontmatter markdown 反序列化。"""
        data = _parse_frontmatter(text, "insight")

        # 解析 JSON 数组字段
        for arr_field in ("evidence", "tags"):
            if arr_field in data and isinstance(data[arr_field], str):
                try:
                    data[arr_field] = json.loads(data[arr_field])
                except json.JSONDecodeError:
                    data[arr_field] = []

        return cls(
            id=data.get("id", ""),
            pattern=data.get("pattern", ""),
            action=data.get("action", ""),
            evidence=data.get("evidence", []),
            scope=_parse_enum(Scope, data.get("scope", "project"), Scope.PROJECT),
            created_at=_parse_datetime(data.get("created_at", "")),
            last_validated_at=_parse_datetime(data.get("last_validated_at", "")),
            evidence_count=int(data.get("evidence_count", 0)),
            confidence=float(data.get("confidence", 0.6)),
            tags=data.get("tags", []),
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
# ID 生成
# ---------------------------------------------------------------------------


def generate_id(prefix: str) -> str:
    """生成 ID: {prefix}_{hex_timestamp}_{random8}。

    Args:
        prefix: ID 前缀，如 'mem' 或 'ins'。

    Returns:
        格式为 {prefix}_{hex_timestamp}_{random8} 的唯一 ID。
    """
    hex_ts = format(int(time.time() * 1000), "x")
    rand8 = secrets.token_hex(4)
    return f"{prefix}_{hex_ts}_{rand8}"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str, label: str = "document") -> dict[str, Any]:
    """解析 YAML frontmatter 块为字典。

    Args:
        text: 完整的 markdown 文本（以 --- 开头）。
        label: 用于错误消息的标签。

    Returns:
        解析后的键值字典。

    Raises:
        ValueError: frontmatter 格式无效。
    """
    if not text.startswith("---"):
        raise ValueError(f"Invalid {label} markdown: missing frontmatter")

    # 查找独立行上的 closing ---
    import re
    match = re.search(r"\n---(?:\n|$)", text[3:])
    if not match:
        raise ValueError(f"Invalid {label} markdown: missing closing ---")
    end = 3 + match.start()
    frontmatter = text[3:end].strip()

    data: dict[str, Any] = {}
    for line in frontmatter.split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = _yaml_unescape(value[1:-1])
        data[key] = value

    return data


def _yaml_unescape(s: str) -> str:
    """反转义 YAML 双引号标量中的转义序列。"""
    return (
        s.replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _parse_enum(enum_cls: type, value: str, default: Any) -> Any:
    """安全解析枚举值，无效时返回默认值。"""
    try:
        return enum_cls(value)
    except ValueError:
        logger.warning(
            "Unknown %s value %r, falling back to %s",
            enum_cls.__name__, value, default,
        )
        return default


def _yaml_quote(s: str) -> str:
    """安全 YAML 字符串引用。

    对所有字符串使用双引号包裹，正确转义特殊字符。
    """
    if not s:
        return '""'
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _parse_datetime(s: str) -> datetime:
    """解析 ISO 8601 日期字符串。"""
    if not s:
        return datetime.now()
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.now()
