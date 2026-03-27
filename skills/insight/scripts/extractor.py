"""Insight 提取引擎。

提供 LLM 调用、JSON 解析、对话格式化等工具函数，
供 CLI 层的 capture/evaluate 命令使用。

同时保留启发式纠正检测（正则 hint），作为 LLM 提取的预筛辅助。
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from typing import Any

from .models import UnifiedMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 纠正模式检测关键词（正则 hint，辅助 LLM 提取）
# ---------------------------------------------------------------------------

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

_EXPLICIT_RE = re.compile(
    "|".join(f"(?:{p})" for p in EXPLICIT_CORRECTION_PATTERNS),
    re.IGNORECASE,
)


def is_correction_hint(content: str) -> bool:
    """判断用户消息是否包含纠正关键词（正则 hint）。

    Args:
        content: 用户消息内容。

    Returns:
        是否匹配纠正关键词。
    """
    if not content:
        return False
    return bool(_EXPLICIT_RE.search(content))


# ---------------------------------------------------------------------------
# 对话格式化
# ---------------------------------------------------------------------------


def format_conversation(messages: list[UnifiedMessage]) -> str:
    """格式化消息列表为可读对话文本。

    Args:
        messages: 统一消息列表。

    Returns:
        格式化的对话文本。
    """
    lines: list[str] = []
    for m in messages:
        role = m.role.value.upper()
        content = m.content[:300] if m.content else ""
        if m.tool_calls:
            tools = ", ".join(tc.name for tc in m.tool_calls)
            content += f"\n[Tool calls: {tools}]"
        lines.append(f"[{role}]: {content}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------


def call_llm(prompt: str, model: str = "sonnet") -> dict[str, Any] | None:
    """调用 LLM 并返回解析后的 JSON。

    通过 pi -p 命令行调用（项目默认 Agent runtime）。
    降级：pi 不可用时回退到 claude -p。

    Args:
        prompt: LLM prompt。
        model: 模型名。

    Returns:
        解析后的 JSON 字典，失败时返回 None。
    """
    for cmd in _LLM_COMMANDS:
        backend_name = "pi" if cmd is _pi_cmd else "claude"
        try:
            result = subprocess.run(
                cmd(prompt, model),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(
                    "LLM backend %s failed (rc=%d): %s",
                    backend_name,
                    result.returncode,
                    result.stderr[:200],
                )
                continue

            logger.info("LLM backend: %s", backend_name)
            text = _unwrap_response(result.stdout, cmd.__name__)
            return extract_json(text)

        except FileNotFoundError:
            logger.warning("%s not found, trying next", backend_name)
            continue
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            logger.error("LLM call error (%s): %s", backend_name, e)
            return None

    logger.error("No LLM backend available (tried pi, claude)")
    return None


def call_llm_array(prompt: str, model: str = "sonnet") -> list[dict[str, Any]]:
    """调用 LLM 并返回 JSON 数组。

    与 call_llm 类似，但期望返回数组。

    Args:
        prompt: LLM prompt。
        model: 模型名。

    Returns:
        JSON 字典列表，失败时返回空列表。
    """
    for cmd in _LLM_COMMANDS:
        backend_name = "pi" if cmd is _pi_cmd else "claude"
        try:
            result = subprocess.run(
                cmd(prompt, model),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning(
                    "LLM backend %s failed (rc=%d): %s",
                    backend_name,
                    result.returncode,
                    result.stderr[:200],
                )
                continue

            logger.info("LLM backend: %s", backend_name)
            text = _unwrap_response(result.stdout, cmd.__name__)
            return _extract_json_array(text)

        except FileNotFoundError:
            logger.warning("%s not found, trying next", backend_name)
            continue
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            logger.error("LLM call error (%s): %s", backend_name, e)
            return []

    logger.error("No LLM backend available (tried pi, claude)")
    return []


def _pi_cmd(prompt: str, model: str) -> list[str]:
    """构造 Pi CLI 命令。"""
    return [
        "pi", "-p", "--no-session", "--mode", "text",
        "--model", model, prompt,
    ]


def _claude_cmd(prompt: str, model: str) -> list[str]:
    """构造 Claude CLI 命令（降级方案）。"""
    return [
        "claude", "-p", "--no-session-persistence",
        "--model", model, "--output-format", "json", prompt,
    ]


_LLM_COMMANDS = [_pi_cmd, _claude_cmd]


def _unwrap_response(stdout: str, backend: str) -> str:
    """从 CLI 输出中提取文本。"""
    if backend == "_claude_cmd":
        try:
            response = json.loads(stdout)
            return response.get("result", stdout)
        except json.JSONDecodeError:
            return stdout
    return stdout


# ---------------------------------------------------------------------------
# JSON 解析
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict[str, Any] | None:
    """从 LLM 输出中提取 JSON 对象。

    Args:
        text: LLM 原始输出。

    Returns:
        解析后的 JSON 字典，失败时返回 None。
    """
    parsed = _parse_json_any(text)
    if parsed is None:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            parsed = _parse_json_any(match.group(1))
    if parsed is None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = _parse_json_any(match.group(0))
    return parsed


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """从 LLM 输出中提取 JSON 数组。

    Args:
        text: LLM 原始输出。

    Returns:
        JSON 字典列表，失败时返回空列表。
    """
    # 先尝试直接解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
        if isinstance(data, dict):
            return [data]
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
            if isinstance(data, dict):
                return [data]
        except (json.JSONDecodeError, ValueError):
            pass

    # 尝试提取 [ ... ] 块
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except (json.JSONDecodeError, ValueError):
            pass

    return []


def _parse_json_any(text: str) -> dict[str, Any] | None:
    """解析 JSON 文本，如果是数组则取第一个元素。"""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


# ---------------------------------------------------------------------------
# 进度显示
# ---------------------------------------------------------------------------


def print_progress(
    done: int,
    total: int,
    valid: int,
    skipped: int,
    failed: int,
) -> None:
    """打印进度条到 stderr。"""
    pct = done * 100 // total if total > 0 else 0
    bar = f"[{'█' * (pct // 5)}{'░' * (20 - pct // 5)}]"
    print(
        f"\r  {bar} {done}/{total}  ✓{valid} ✗{skipped} ⚠{failed}",
        end="",
        file=sys.stderr,
        flush=True,
    )
