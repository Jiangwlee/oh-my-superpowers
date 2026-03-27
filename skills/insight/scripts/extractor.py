"""Insight 提取引擎。

两阶段流程：
1. 启发式预过滤：从统一消息流中识别纠正模式候选片段
2. LLM 精筛：将候选片段送给 LLM 提炼为 Insight schema

双路数据管道：
- 显式纠正：用户直接说"不对"/"错了"/"应该是" → 高信噪比，优先处理
- 隐式纠正：反复尝试/路径偏离 → 高价值但高成本，延迟处理
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime
from typing import Any

from .models import (
    CorrectionExample,
    CorrectionTrajectory,
    Insight,
    InsightScope,
    MessageRole,
    UnifiedMessage,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 纠正模式检测关键词
# ---------------------------------------------------------------------------

# 显式纠正（用户明确否定/纠正）
EXPLICIT_CORRECTION_PATTERNS = [
    r"不对",
    r"不是",
    r"错了",
    r"不要",
    r"别这样",
    r"不应该",
    r"应该是",
    r"请改为",
    r"请改成",
    r"重新",
    r"again",
    r"wrong",
    r"no[,.\s]",
    r"that'?s not",
    r"don'?t",
    r"shouldn'?t",
    r"instead",
    r"actually",
    r"而不是",
    r"但是.{0,10}不",
    r"我说的是",
    r"你理解错了",
    r"不需要",
    r"去掉",
    r"删掉",
    r"取消",
]

# 编译正则
_EXPLICIT_RE = re.compile(
    "|".join(f"(?:{p})" for p in EXPLICIT_CORRECTION_PATTERNS),
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Phase 1：启发式预过滤
# ---------------------------------------------------------------------------


def detect_correction_patterns(
    messages: list[UnifiedMessage],
    window_size: int = 6,
) -> list[CorrectionTrajectory]:
    """从消息流中检测纠正模式。

    策略：滑动窗口扫描，当用户消息匹配纠正关键词时，
    提取前后上下文组成纠正轨迹候选。

    Args:
        messages: 统一消息列表（按时间排序）。
        window_size: 上下文窗口大小（纠正点前后各取多少条）。

    Returns:
        CorrectionTrajectory 列表。
    """
    trajectories: list[CorrectionTrajectory] = []

    for i, msg in enumerate(messages):
        if not msg.is_user:
            continue
        if not _is_correction(msg.content):
            continue

        # 找到纠正点，提取上下文窗口
        start = max(0, i - window_size)
        end = min(len(messages), i + window_size + 1)
        window = messages[start:end]

        # 提取纠正前的助手行为
        before_msg = _find_preceding_assistant(messages, i)
        # 提取纠正后的助手行为
        after_msg = _find_following_assistant(messages, i)

        if before_msg is None or after_msg is None:
            continue

        trajectory = CorrectionTrajectory(
            trigger=_summarize_context(window[:i - start]),
            wrong_behavior=_extract_behavior(before_msg),
            corrected_behavior=_extract_behavior(after_msg),
            messages=window,
            correction_count=1,
            session_id=msg.session_id,
            runtime=msg.runtime,
        )
        trajectories.append(trajectory)

    # 合并相邻的纠正（同一个 session 中连续纠正视为同一轨迹）
    return _merge_adjacent(trajectories)


def _is_correction(content: str) -> bool:
    """判断用户消息是否为纠正。"""
    if not content:
        return False
    return bool(_EXPLICIT_RE.search(content))


def _find_preceding_assistant(
    messages: list[UnifiedMessage], idx: int
) -> UnifiedMessage | None:
    """向前查找最近的助手消息。"""
    for i in range(idx - 1, -1, -1):
        if messages[i].is_assistant:
            return messages[i]
    return None


def _find_following_assistant(
    messages: list[UnifiedMessage], idx: int
) -> UnifiedMessage | None:
    """向后查找最近的助手消息。"""
    for i in range(idx + 1, len(messages)):
        if messages[i].is_assistant:
            return messages[i]
    return None


def _extract_behavior(msg: UnifiedMessage) -> str:
    """从助手消息中提取行为描述。"""
    parts: list[str] = []
    if msg.content:
        # 截取前 500 字符作为行为描述
        parts.append(msg.content[:500])
    if msg.tool_calls:
        for tc in msg.tool_calls:
            parts.append(f"[Tool: {tc.name}]")
    return "\n".join(parts) if parts else "(no content)"


def _summarize_context(msgs: list[UnifiedMessage]) -> str:
    """将上下文消息压缩为简短描述。"""
    parts: list[str] = []
    for m in msgs:
        if m.is_user and m.content:
            parts.append(m.content[:200])
    return " → ".join(parts) if parts else ""


def _merge_adjacent(
    trajectories: list[CorrectionTrajectory],
) -> list[CorrectionTrajectory]:
    """合并同一 session 中相邻的纠正轨迹。"""
    if len(trajectories) <= 1:
        return trajectories

    merged: list[CorrectionTrajectory] = [trajectories[0]]
    for t in trajectories[1:]:
        prev = merged[-1]
        # 同一 session 且时间窗口重叠 → 合并
        if (
            t.session_id == prev.session_id
            and t.messages
            and prev.messages
            and _messages_overlap(prev.messages, t.messages)
        ):
            prev.correction_count += 1
            prev.corrected_behavior = t.corrected_behavior
            prev.messages.extend(
                m for m in t.messages if m not in prev.messages
            )
        else:
            merged.append(t)

    return merged


def _messages_overlap(a: list[UnifiedMessage], b: list[UnifiedMessage]) -> bool:
    """检查两组消息是否有重叠。"""
    a_ids = {m.message_id for m in a if m.message_id}
    b_ids = {m.message_id for m in b if m.message_id}
    return bool(a_ids & b_ids)


# ---------------------------------------------------------------------------
# Phase 2：LLM 精筛
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """你是一个经验提取专家。请分析以下对话片段中的纠正模式，提取 behavioral delta（行为差分）。

对话片段：
{conversation}

请以 JSON 格式输出，包含以下字段：
- trigger: 什么情况/上下文触发了错误行为（一句话描述）
- wrong_default: 助手的错误默认行为（具体描述做了什么错事）
- corrected_behavior: 用户纠正后的正确行为（具体描述应该怎么做）
- why: 为什么原来的做法是错的（可选，简短解释）
- tags: 相关标签列表（如 "code-style", "architecture", "testing" 等）
- scope: "project"（仅限此项目）或 "user"（通用经验）
- is_valid: 这是否是一个真正有价值的 behavioral delta（true/false）
- confidence: 对此 insight 的置信度（0.0-1.0）

只输出 JSON，不要其他文本。如果这不是一个有意义的纠正模式，设 is_valid 为 false。"""


def generate_insights(
    trajectories: list[CorrectionTrajectory],
    model: str = "sonnet",
    dry_run: bool = False,
) -> list[Insight]:
    """将纠正轨迹提炼为 Insight。

    Args:
        trajectories: 纠正轨迹列表。
        model: LLM 模型选择。
        dry_run: 仅输出候选，不调用 LLM。

    Returns:
        Insight 列表。
    """
    insights: list[Insight] = []

    for trajectory in trajectories:
        if dry_run:
            # dry-run 模式：直接从启发式结果构造 Insight
            insight = _trajectory_to_insight(trajectory)
            insights.append(insight)
            continue

        # 构造对话上下文
        conversation = _format_conversation(trajectory.messages)
        prompt = EXTRACTION_PROMPT.format(conversation=conversation)

        # 调用 LLM
        result = _call_llm(prompt, model)
        if result is None:
            logger.warning("LLM extraction failed for session %s", trajectory.session_id)
            continue

        if not result.get("is_valid", False):
            logger.debug("LLM judged trajectory as not valid, skipping")
            continue

        insight = Insight(
            id=Insight.generate_id(
                result.get("trigger", ""),
                result.get("wrong_default", ""),
            ),
            trigger=result.get("trigger", trajectory.trigger),
            wrong_default=result.get("wrong_default", trajectory.wrong_behavior),
            corrected_behavior=result.get("corrected_behavior", trajectory.corrected_behavior),
            examples=[
                CorrectionExample(
                    session_id=trajectory.session_id,
                    before=trajectory.wrong_behavior[:500],
                    after=trajectory.corrected_behavior[:500],
                    context=trajectory.trigger,
                )
            ],
            tags=result.get("tags", []),
            correction_count=trajectory.correction_count,
            confidence=result.get("confidence", 0.5),
            first_seen=trajectory.messages[0].timestamp if trajectory.messages else datetime.now(),
            last_confirmed=trajectory.messages[-1].timestamp if trajectory.messages else datetime.now(),
            scope=InsightScope(result.get("scope", "project")),
            why=result.get("why", ""),
            source_session_ids=[trajectory.session_id],
        )
        insights.append(insight)

    return insights


def _trajectory_to_insight(trajectory: CorrectionTrajectory) -> Insight:
    """启发式：直接从轨迹构造 Insight（无 LLM）。"""
    return Insight(
        id=Insight.generate_id(trajectory.trigger, trajectory.wrong_behavior),
        trigger=trajectory.trigger,
        wrong_default=trajectory.wrong_behavior[:500],
        corrected_behavior=trajectory.corrected_behavior[:500],
        examples=[
            CorrectionExample(
                session_id=trajectory.session_id,
                before=trajectory.wrong_behavior[:500],
                after=trajectory.corrected_behavior[:500],
                context=trajectory.trigger,
            )
        ],
        correction_count=trajectory.correction_count,
        confidence=0.3,  # 未经 LLM 验证，低置信度
        first_seen=trajectory.messages[0].timestamp if trajectory.messages else datetime.now(),
        last_confirmed=trajectory.messages[-1].timestamp if trajectory.messages else datetime.now(),
        scope=InsightScope.PROJECT,
        source_session_ids=[trajectory.session_id],
    )


def _format_conversation(messages: list[UnifiedMessage]) -> str:
    """格式化消息列表为可读对话文本。"""
    lines: list[str] = []
    for m in messages:
        role = m.role.value.upper()
        content = m.content[:300] if m.content else ""
        if m.tool_calls:
            tools = ", ".join(tc.name for tc in m.tool_calls)
            content += f"\n[Tool calls: {tools}]"
        lines.append(f"[{role}]: {content}")
    return "\n\n".join(lines)


def _call_llm(prompt: str, model: str = "sonnet") -> dict[str, Any] | None:
    """调用 LLM 提取 insight。

    通过 claude -p 命令行调用，避免 SDK 依赖。
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "json", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error("LLM call failed: %s", result.stderr[:200])
            return None

        # claude --output-format json 输出结构中 result 字段是文本
        response = json.loads(result.stdout)
        text = response.get("result", result.stdout)

        # 从文本中提取 JSON
        return _extract_json(text)

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        logger.error("LLM call error: %s", e)
        return None


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 LLM 输出中提取 JSON 对象。"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 { ... } 块
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None
