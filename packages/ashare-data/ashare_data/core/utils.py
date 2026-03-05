"""通用工具函数。

提供数值转换、日期处理等通用工具，供各模块复用。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 时区
_CN_TZ = timezone.utc  # 中国时区在需要时通过 timedelta 设置


def now_cn() -> datetime:
    """返回当前中国时间（UTC+8）。"""
    return datetime.now(timezone.utc).astimezone(_CN_TZ)


def today_cn_ymd() -> str:
    """返回当前中国日期，格式 YYYYMMDD。"""
    return now_cn().strftime("%Y%m%d")


def today_cn_iso() -> str:
    """返回当前中国日期，格式 YYYY-MM-DD。"""
    return now_cn().strftime("%Y-%m-%d")


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数。

    Args:
        value: 待转换值。
        default: 转换失败时的默认值。

    Returns:
        转换后的浮点数，或默认值。
    """
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_float(value: Any, default: float = 0.0) -> float:
    """解析可能带逗号的浮点数字符串。

    Args:
        value: 待解析值。
        default: 解析失败时的默认值。

    Returns:
        解析后的浮点数，或默认值。
    """
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def norm_price(value: Any) -> float:
    """规范化价格。

    处理金融数据常见的以"分"或"厘"为单位的整数价格。
    - 小于等于 1000 的值视为"元"
    - 大于 1000 的值除以 10000 转为"元"

    Args:
        value: 价格值。

    Returns:
        规范化后的价格（元）。
    """
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0
    return x / 10000.0 if abs(x) > 1000 else x


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数。

    Args:
        value: 待转换值。
        default: 转换失败时的默认值。

    Returns:
        转换后的整数，或默认值。
    """
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def atomic_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, target)


def atomic_write_json(path: str | Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
