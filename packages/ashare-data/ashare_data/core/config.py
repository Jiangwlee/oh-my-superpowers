"""统一路径与目录配置（固定使用默认路径）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# 固定使用默认目录，避免环境变量导致路径歧义。
ASHARE_HOME = Path("~/.ashare-assistant").expanduser()
CACHE_DIR = ASHARE_HOME / "cache"
DATA_DIR = ASHARE_HOME / "data"
MEMORY_DIR = ASHARE_HOME / "memory"
BROKER_DIR = ASHARE_HOME / "broker_data"
DECISION_LOG = MEMORY_DIR / "decision_log.jsonl"

_DEFAULT_CACHE_CATEGORIES = (
    "kline",
    "broker",
    "news",
    "taoguba",
    "eastmoney",
    "ths",
    "funding",
)


def data_dir_for_date(date_str: str | None = None) -> Path:
    """返回指定日期的数据目录。"""
    date_value = date_str or datetime.now().strftime("%Y-%m-%d")
    return DATA_DIR / date_value


def ensure_dirs() -> dict[str, str]:
    """创建统一目录结构（幂等）。"""
    for path in (ASHARE_HOME, CACHE_DIR, DATA_DIR, MEMORY_DIR, BROKER_DIR):
        path.mkdir(parents=True, exist_ok=True)
    for category in _DEFAULT_CACHE_CATEGORIES:
        (CACHE_DIR / category).mkdir(parents=True, exist_ok=True)
    return {
        "home": str(ASHARE_HOME),
        "cache": str(CACHE_DIR),
        "data": str(DATA_DIR),
        "memory": str(MEMORY_DIR),
        "broker": str(BROKER_DIR),
        "decision_log": str(DECISION_LOG),
    }
