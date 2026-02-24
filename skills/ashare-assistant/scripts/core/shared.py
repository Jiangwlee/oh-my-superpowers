"""holding_insight / trade_review 公共函数。"""

from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

CN_TZ = timezone(timedelta(hours=8))
DEFAULT_STRATEGY = {
    "strategy_version": "unknown",
    "trend_stock": {"position": "单只不超过总仓位20%"},
    "theme_stock": {"position": "单只不超过总仓位15%"},
    "market_position": {"strong": "60-80%", "neutral": "30-50%", "weak": "10-20%"},
}


def now_cn_iso() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def today_cn() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def norm_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if "." in text:
        text = text.split(".")[0]
    if text.startswith(("SH", "SZ", "BJ")) and len(text) > 2:
        text = text[2:]
    return text.zfill(6) if text.isdigit() and len(text) < 6 else text


def extract_pct_limit(text: str, fallback: float) -> float:
    """解析单值仓位限制，返回比例（0-1）。如 20% -> 0.2。"""
    raw = str(text or "")
    num = ""
    last_num = ""
    for ch in raw:
        if ch.isdigit() or ch == ".":
            num += ch
        else:
            if num:
                last_num = num
                num = ""
    if num:
        last_num = num
    if not last_num:
        return fallback
    v = safe_float(last_num, fallback * 100)
    return v / 100.0 if v > 1 else v


def parse_range_to_pct(text: str) -> tuple[float, float] | None:
    """解析仓位区间，返回百分数字段（0-100）。如 6-8成 -> (60, 80)。"""
    raw = str(text or "")
    nums: list[float] = []
    current = ""
    for ch in raw:
        if ch.isdigit() or ch == ".":
            current += ch
        else:
            if current:
                nums.append(safe_float(current))
                current = ""
    if current:
        nums.append(safe_float(current))
    if len(nums) < 2:
        return None
    scale = 10.0 if "成" in raw and "%" not in raw else 1.0
    return nums[0] * scale, nums[1] * scale


def parse_range_to_percent_points(text: str) -> tuple[float, float] | None:
    """parse_range_to_pct 的显式命名别名（单位：百分数点，0-100）。"""
    return parse_range_to_pct(text)


def load_strategy(yaml_path: str, logger: logging.Logger | None = None) -> dict[str, Any]:
    path = Path(yaml_path)
    if not path.exists():
        return copy.deepcopy(DEFAULT_STRATEGY)
    if yaml is None:
        if logger:
            logger.warning("PyYAML 不可用，使用内置默认策略值")
        return copy.deepcopy(DEFAULT_STRATEGY)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            return copy.deepcopy(DEFAULT_STRATEGY)
        merged = copy.deepcopy(DEFAULT_STRATEGY)
        merged.update(data)
        return merged
    except Exception:
        if logger:
            logger.exception("读取策略文件失败: %s", yaml_path)
        return copy.deepcopy(DEFAULT_STRATEGY)


def determine_account_mode(total: float, hold_earn: float) -> str:
    if total <= 0:
        return "normal"
    pnl_pct = hold_earn / total
    if pnl_pct <= -0.30:
        return "critical"
    if pnl_pct <= -0.10:
        return "defensive"
    if pnl_pct >= 0.20:
        return "growth"
    return "normal"


def position_market_value(pos: dict[str, Any]) -> float:
    mv = safe_float(
        pos.get("market_value")
        or pos.get("marketValue")
        or pos.get("value")
        or pos.get("market_val")
    )
    if mv > 0:
        return mv
    vol = safe_float(pos.get("hold_vol") or pos.get("volume") or pos.get("qty"))
    price = safe_float(
        pos.get("last_price")
        or pos.get("current_price")
        or pos.get("price")
        or pos.get("cost_price")
    )
    return vol * price


def holding_days_from_history(code: str, history: dict[str, Any]) -> int:
    positions_map = history.get("positions") if isinstance(history, dict) else {}
    if not isinstance(positions_map, dict):
        return 0
    days = 0
    for date in sorted(positions_map.keys(), reverse=True):
        snap = positions_map.get(date)
        hold_list = snap.get("hold_list") if isinstance(snap, dict) else []
        found = False
        for pos in hold_list if isinstance(hold_list, list) else []:
            if isinstance(pos, dict) and norm_code(pos.get("code")) == code:
                found = True
                days += 1
                break
        if not found:
            break
    return days


def enrich_hold_list_prices(
    hold_list: list[dict[str, Any]],
    *,
    fetch_daily_kline: Callable[[str, int], list[dict[str, Any]]],
    logger: logging.Logger | None = None,
) -> None:
    """为缺少现价/市值的持仓回填 JRJ 日K线最新收盘价（原地修改）。"""
    need_price: list[dict[str, Any]] = []
    for pos in hold_list:
        if not isinstance(pos, dict):
            continue
        has_price = (
            safe_float(
                pos.get("last_price")
                or pos.get("current_price")
                or pos.get("price")
                or pos.get("market_value")
            )
            > 0
        )
        if not has_price:
            need_price.append(pos)
    if not need_price:
        return

    codes = [norm_code(p.get("code")) for p in need_price if norm_code(p.get("code"))]
    if not codes:
        return

    daily_map: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(codes))) as pool:
        futs = {pool.submit(fetch_daily_kline, code, 5): code for code in codes}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                daily_map[code] = fut.result() or []
            except Exception:
                if logger:
                    logger.exception("enrich: 获取日K失败: %s", code)
                daily_map[code] = []

    for pos in need_price:
        code = norm_code(pos.get("code"))
        bars = daily_map.get(code, [])
        if not bars:
            continue
        closes = [safe_float(b.get("close")) for b in bars if safe_float(b.get("close")) > 0]
        if not closes:
            continue
        latest_price = closes[-1]
        pos["last_price"] = latest_price
        vol = safe_float(pos.get("hold_vol") or pos.get("volume") or pos.get("qty"))
        if vol > 0:
            pos["market_value"] = round(vol * latest_price, 2)
