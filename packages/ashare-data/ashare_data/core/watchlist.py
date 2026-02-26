"""Watchlist 持久化管理。

追踪曾出现过 is_uptrend=True + 4★ 的股票，即使其退出东方财富人气榜，
每日仍继续用相同趋势逻辑扫描，并检测 MA5/MA10 ±2% 买入信号。

watchlist.json 格式::

    {
      "updated": "2026-02-26",
      "stocks": [
        {
          "code": "601231",
          "name": "环旭电子",
          "added_date": "2026-02-20",
          "status": "active",
          "cooling_since": null
        }
      ]
    }
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from ashare_data.core.config import MEMORY_DIR

if TYPE_CHECKING:
    from ashare_data.fetchers.trend_scanner import TrendResult

logger = logging.getLogger(__name__)

WATCHLIST_PATH = MEMORY_DIR / "watchlist.json"

_COOLING_DAYS = 3
_MIN_STAR = 4

Stock = dict[str, Any]


def load() -> list[Stock]:
    """读取 watchlist.json，文件不存在时返回空列表。

    Returns:
        股票列表，每项含 code/name/added_date/status/cooling_since。
    """
    if not WATCHLIST_PATH.exists():
        return []
    try:
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stocks", [])
    except Exception:
        logger.exception("读取 watchlist.json 失败")
        return []


def save(stocks: list[Stock], today: str | None = None) -> None:
    """将股票列表写回 watchlist.json。

    Args:
        stocks: 股票列表。
        today: 更新日期字符串（YYYY-MM-DD），默认取当天。
    """
    from datetime import datetime

    date_str = today or datetime.now().strftime("%Y-%m-%d")
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data = {"updated": date_str, "stocks": stocks}
    try:
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("写入 watchlist.json 失败")


def get_extra_candidates(exclude_codes: set[str]) -> list[dict[str, Any]]:
    """返回 watchlist 中不在东方财富候选池的股票，格式兼容 scan_all 输入。

    Args:
        exclude_codes: 已经在候选池中的股票代码集合（排除重复）。

    Returns:
        候选列表，每项含 code/sc/name/rank/from 字段。
    """
    stocks = load()
    extras: list[dict[str, Any]] = []
    for s in stocks:
        code = s.get("code", "")
        if not code or code in exclude_codes:
            continue
        if s.get("status") not in ("active", "cooling"):
            continue
        # 构造 sc：沪市 6 开头用 SH，其余用 SZ
        prefix = "SH" if code.startswith("6") else "SZ"
        extras.append(
            {
                "code": code,
                "sc": f"{prefix}{code}",
                "name": s.get("name", code),
                "rank": 0,
                "from": "watchlist",
            }
        )
    return extras


def update_from_scan(scan_results: list["TrendResult"], today: str) -> None:
    """根据最新扫描结果维护 watchlist 状态。

    规则：
    - 新增：is_uptrend=True + star_rating >= 4 且不在 watchlist → 自动入池
    - 冷却：watchlist 股 is_uptrend=False + status=active → cooling_since=today
    - 恢复：cooling 股 is_uptrend=True → 重置为 active
    - 移除：cooling_since 超过 _COOLING_DAYS 日 → 删除

    Args:
        scan_results: 本次扫描的 TrendResult 列表（含 watchlist 补充股）。
        today: 当前日期字符串 YYYY-MM-DD。
    """
    from datetime import date

    stocks = load()
    existing_codes = {s["code"] for s in stocks}

    # 建立扫描结果索引
    result_map: dict[str, "TrendResult"] = {r.code: r for r in scan_results}

    # 1. 新增：is_uptrend=True + 4★ 且不在 watchlist
    for r in scan_results:
        if r.code not in existing_codes and r.is_uptrend and r.star_rating >= _MIN_STAR:
            stocks.append(
                {
                    "code": r.code,
                    "name": r.name,
                    "added_date": today,
                    "status": "active",
                    "cooling_since": None,
                }
            )
            existing_codes.add(r.code)
            logger.debug("watchlist 新增: %s %s", r.code, r.name)

    # 2. 更新现有 watchlist 股状态
    today_date = date.fromisoformat(today)
    kept: list[Stock] = []
    for s in stocks:
        code = s["code"]
        r = result_map.get(code)

        if r is None:
            # 本次扫描未覆盖（理论上不应发生，因为 get_extra_candidates 已补入）
            kept.append(s)
            continue

        status = s.get("status", "active")

        if r.is_uptrend:
            # 恢复：无论 cooling 还是 active，均重置为 active
            s["status"] = "active"
            s["cooling_since"] = None
        else:
            if status == "active":
                # 进入冷却
                s["status"] = "cooling"
                s["cooling_since"] = today
            elif status == "cooling":
                cooling_since_str = s.get("cooling_since") or today
                try:
                    cooling_date = date.fromisoformat(cooling_since_str)
                    elapsed = (today_date - cooling_date).days
                except ValueError:
                    elapsed = 0
                if elapsed >= _COOLING_DAYS:
                    logger.debug(
                        "watchlist 移除（冷却%d天）: %s %s", elapsed, code, s.get("name", "")
                    )
                    continue  # 不加入 kept → 等效移除

        kept.append(s)

    save(kept, today)
    logger.debug(
        "watchlist 更新完成: 共 %d 只（active=%d, cooling=%d）",
        len(kept),
        sum(1 for s in kept if s.get("status") == "active"),
        sum(1 for s in kept if s.get("status") == "cooling"),
    )
