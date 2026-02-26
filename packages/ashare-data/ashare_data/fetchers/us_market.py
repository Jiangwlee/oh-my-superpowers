"""美股主要指数与核心科技股行情抓取模块。

数据来源（均无需认证，直连可用）：
- 个股 (NVDA/AAPL/TSLA/MSFT/GOOG/META)：
    腾讯财经实时行情接口 qt.gtimg.cn，代码格式：usNVDA
- 指数 (纳斯达克/道琼斯/标普500/VIX)：
    腾讯财经实时行情接口 qt.gtimg.cn，代码格式：us.IXIC

字段格式（tilde 分隔，0-indexed）：
    [3] 当前价 (close)
    [4] 昨收 (prev_close)
    [32] 涨跌幅%

market_status 基于北京时间推算美东时间：
- 夏令时 (3月第2个周日 ~ 11月第1个周日)：美东 = UTC - 4h
- 冬令时：美东 = UTC - 5h
- 交易时间 09:30–16:00 美东 → open；盘前/盘后/周末 → pre-market/after-hours/closed
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_bytes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_TENCENT_URL = "https://qt.gtimg.cn/q={symbols}"
_TENCENT_HEADERS = {
    "Referer": "https://finance.qq.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/147.0"
    ),
}

_INDICES = [
    {"ticker": "^IXIC", "name_cn": "纳斯达克", "gtimg_sym": "us.IXIC"},
    {"ticker": "^DJI", "name_cn": "道琼斯", "gtimg_sym": "us.DJI"},
    {"ticker": "^GSPC", "name_cn": "标普500", "gtimg_sym": "us.INX"},
    {"ticker": "^VIX", "name_cn": "VIX恐慌指数", "gtimg_sym": "us.VIX"},
]

_TECH_STOCKS = [
    {"ticker": "NVDA", "name_cn": "英伟达", "gtimg_sym": "usNVDA"},
    {"ticker": "AAPL", "name_cn": "苹果", "gtimg_sym": "usAAPL"},
    {"ticker": "TSLA", "name_cn": "特斯拉", "gtimg_sym": "usTSLA"},
    {"ticker": "MSFT", "name_cn": "微软", "gtimg_sym": "usMSFT"},
    {"ticker": "GOOG", "name_cn": "谷歌", "gtimg_sym": "usGOOG"},
    {"ticker": "META", "name_cn": "Meta", "gtimg_sym": "usMETA"},
]

_SECTOR_MAP: dict[str, list[str]] = {
    "NVDA": ["半导体/芯片", "AI算力", "光模块", "液冷散热"],
    "AAPL": ["消费电子", "果链（立讯精密/歌尔股份）", "AI手机"],
    "TSLA": ["新能源汽车", "锂电池", "充电桩", "汽车智能化"],
    "MSFT": ["云计算", "AI应用软件", "企业SaaS"],
    "GOOG": ["AI应用", "算力产业链", "光模块/液冷"],
    "META": ["VR/AR/元宇宙", "AI应用", "液冷散热"],
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _safe_float(value: Any) -> float | None:
    """安全转 float，失败返回 None。"""
    try:
        if value is None:
            return None
        f = float(str(value).replace(",", ""))
        return round(f, 2)
    except (TypeError, ValueError):
        return None


def _market_status_by_time(now_utc: datetime | None = None) -> str:
    """根据当前 UTC 时间推算美股市场状态。

    判断逻辑：
    - 周六/周日 → "closed"
    - 美东时间 09:30–16:00（交易时段）→ "open"
    - 美东时间 04:00–09:30（盘前）→ "pre-market"
    - 美东时间 16:00–20:00（盘后）→ "after-hours"
    - 其他 → "closed"

    夏令时 (DST) 判断：3 月第 2 个周日 ~ 11 月第 1 个周日为夏令时。
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    year = now_utc.year

    # 3 月第 2 个周日
    mar1 = datetime(year, 3, 1, tzinfo=timezone.utc)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)

    # 11 月第 1 个周日
    nov1 = datetime(year, 11, 1, tzinfo=timezone.utc)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)

    is_dst = (
        dst_start
        <= now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        < dst_end
    )
    offset_hours = -4 if is_dst else -5  # EDT or EST
    eastern = now_utc + timedelta(hours=offset_hours)

    weekday = eastern.weekday()  # 0=Mon, 6=Sun
    if weekday >= 5:
        return "closed"

    t = eastern.hour * 60 + eastern.minute
    if 9 * 60 + 30 <= t < 16 * 60:
        return "open"
    if 4 * 60 <= t < 9 * 60 + 30:
        return "pre-market"
    if 16 * 60 <= t < 20 * 60:
        return "after-hours"
    return "closed"


# ---------------------------------------------------------------------------
# 行情抓取：腾讯财经（个股+指数统一接口）
# ---------------------------------------------------------------------------


def _fetch_gtimg(syms: list[str]) -> dict[str, dict[str, float | None]]:
    """批量获取美股行情（腾讯财经 qt.gtimg.cn，个股+指数均支持）。

    Args:
        syms: gtimg 代码列表，如 ["usNVDA", "us.IXIC"]

    Returns:
        {gtimg_sym: {"close": float|None, "prev_close": float|None, "change_pct": float|None}}
        请求失败时所有 sym 的三个字段均为 None。
    """
    result: dict[str, dict[str, float | None]] = {
        s: {"close": None, "prev_close": None, "change_pct": None} for s in syms
    }
    url = _TENCENT_URL.format(symbols=",".join(syms))
    try:
        raw = http_bytes(url, headers=_TENCENT_HEADERS, timeout=10)
        text = raw.decode("gbk", errors="replace")
        for line in text.strip().splitlines():
            # v_usNVDA="..." 或 v_us.IXIC="..."
            m = re.match(r'v_([^=]+)="([^"]*)"', line.strip())
            if not m:
                continue
            sym = m.group(1)
            if sym not in result:
                continue
            fields = m.group(2).split("~")
            if len(fields) < 5:
                continue
            close = _safe_float(fields[3])
            prev_close = _safe_float(fields[4])
            change_pct = _safe_float(fields[32]) if len(fields) > 32 else None
            # 如果 change_pct 缺失但 close/prev_close 都有，自行计算
            if (
                change_pct is None
                and close is not None
                and prev_close
                and prev_close != 0
            ):
                change_pct = round((close - prev_close) / prev_close * 100, 2)
            result[sym] = {
                "close": close,
                "prev_close": prev_close,
                "change_pct": change_pct,
            }
    except Exception:
        logger.exception("腾讯财经行情获取失败")
    return result


# ---------------------------------------------------------------------------
# 主接口
# ---------------------------------------------------------------------------


def fetch_us_market() -> dict[str, Any]:
    """获取美股主要指数和核心科技股行情。

    数据来源：腾讯财经 qt.gtimg.cn（个股+指数统一接口）

    Returns:
        {
            "fetched_at": "2026-02-24 21:30:00",
            "market_status": "closed|open|pre-market|after-hours",
            "indices": [{"ticker", "name_cn", "change_pct", "close", "prev_close"}, ...],
            "tech_stocks": [{"ticker", "name_cn", "change_pct", "close", "prev_close",
                             "a_share_sectors"}, ...],
        }
    """
    cache_day = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"us_market_daily_{cache_day}"
    cached = cache_get("market", cache_key)
    if isinstance(cached, dict):
        return cached

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    market_status = _market_status_by_time()

    # 一次性批量获取所有个股+指数
    all_syms = [cfg["gtimg_sym"] for cfg in _INDICES] + [
        cfg["gtimg_sym"] for cfg in _TECH_STOCKS
    ]
    quotes = _fetch_gtimg(all_syms)

    # --- 指数 ---
    indices: list[dict[str, Any]] = []
    for cfg in _INDICES:
        q = quotes.get(cfg["gtimg_sym"], {})
        indices.append(
            {
                "ticker": cfg["ticker"],
                "name_cn": cfg["name_cn"],
                "change_pct": q.get("change_pct"),
                "close": q.get("close"),
                "prev_close": q.get("prev_close"),
            }
        )

    # --- 个股 ---
    tech_stocks: list[dict[str, Any]] = []
    for cfg in _TECH_STOCKS:
        q = quotes.get(cfg["gtimg_sym"], {})
        tech_stocks.append(
            {
                "ticker": cfg["ticker"],
                "name_cn": cfg["name_cn"],
                "change_pct": q.get("change_pct"),
                "close": q.get("close"),
                "prev_close": q.get("prev_close"),
                "a_share_sectors": _SECTOR_MAP.get(cfg["ticker"], []),
            }
        )

    result: dict[str, Any] = {
        "fetched_at": fetched_at,
        "market_status": market_status,
        "indices": indices,
        "tech_stocks": tech_stocks,
    }
    cache_set("market", cache_key, result, ttl_seconds=None)
    return result
