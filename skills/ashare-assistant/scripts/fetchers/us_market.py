"""美股主要指数与核心科技股行情抓取模块。

使用 yfinance 获取收盘价和涨跌幅，并附带硬编码的 A 股关联板块映射。
若 yfinance 未安装，函数返回空结构并记录警告，不抛出异常。
"""

import logging
from datetime import datetime
from typing import Any

from scripts.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

try:
    import yfinance as yf

    _YF_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    _YF_AVAILABLE = False
    logger.warning("yfinance 未安装，美股行情采集将被跳过。安装：pip install yfinance")





_INDICES = [
    {"ticker": "^IXIC", "name_cn": "纳斯达克"},
    {"ticker": "^DJI", "name_cn": "道琼斯"},
    {"ticker": "^GSPC", "name_cn": "标普500"},
    {"ticker": "^VIX", "name_cn": "VIX恐慌指数"},
]

_TECH_STOCKS = [
    {"ticker": "NVDA", "name_cn": "英伟达"},
    {"ticker": "AAPL", "name_cn": "苹果"},
    {"ticker": "TSLA", "name_cn": "特斯拉"},
    {"ticker": "MSFT", "name_cn": "微软"},
    {"ticker": "GOOG", "name_cn": "谷歌"},
    {"ticker": "META", "name_cn": "Meta"},
]

_SECTOR_MAP: dict[str, list[str]] = {
    "NVDA": ["半导体/芯片", "AI算力", "光模块", "液冷散热"],
    "AAPL": ["消费电子", "果链（立讯精密/歌尔股份）", "AI手机"],
    "TSLA": ["新能源汽车", "锂电池", "充电桩", "汽车智能化"],
    "MSFT": ["云计算", "AI应用软件", "企业SaaS"],
    "GOOG": ["AI应用", "算力产业链", "光模块/液冷"],
    "META": ["VR/AR/元宇宙", "AI应用", "液冷散热"],
}


def _safe_round(value: Any) -> float | None:
    """转 float 并保留两位小数，失败返回 None。"""
    try:
        if value is None:
            return None
        number = float(value)
        return round(number, 2)
    except (TypeError, ValueError):
        return None


def _get_quote(ticker_sym: str) -> dict[str, float | str | None]:
    """获取单个标的的行情数据。

    Args:
        ticker_sym: Yahoo Finance Ticker 符号，如 "^IXIC" 或 "NVDA"。

    Returns:
        包含 prev_close / close / change_pct / market_status 的 dict。
        任何字段获取失败时对应值为 None。
    """
    try:
        ticker = yf.Ticker(ticker_sym)
        info = ticker.fast_info
        prev_close = _safe_round(getattr(info, "previous_close", None))
        close = _safe_round(getattr(info, "last_price", None))
        market_status = getattr(info, "market_state", None)

        change_pct: float | None = None
        if prev_close is not None and close is not None and prev_close != 0:
            change_pct = round((close - prev_close) / prev_close * 100, 2)

        return {
            "prev_close": prev_close,
            "close": close,
            "change_pct": change_pct,
            "market_status": market_status,
        }
    except Exception as exc:
        logger.warning("获取 %s 行情失败: %s", ticker_sym, exc)
        return {"prev_close": None, "close": None, "change_pct": None, "market_status": None}


def fetch_us_market() -> dict[str, Any]:
    """获取美股主要指数和核心科技股行情。

    Returns:
        {
            "fetched_at": "2026-02-21 21:30:00",
            "market_status": "closed|open|pre-market|after-hours|unavailable",
            "indices": [{"ticker", "name_cn", "change_pct", "close", "prev_close"}, ...],
            "tech_stocks": [{"ticker", "name_cn", "change_pct", "close", "prev_close",
                             "a_share_sectors"}, ...],
        }
        yfinance 未安装时，market_status 为 "unavailable"，indices/tech_stocks 为空列表，
        并附带 "error" 字段说明原因。
    """
    cache_day = datetime.now().strftime("%Y-%m-%d")
    is_mock_yf = bool(yf is not None and yf.__class__.__module__.startswith("unittest.mock"))
    cache_key = f"us_market_daily_{cache_day}"
    if _YF_AVAILABLE and not is_mock_yf:
        cached = cache_get("market", cache_key)
        if isinstance(cached, dict):
            return cached
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not _YF_AVAILABLE:
        result = {
            "fetched_at": fetched_at,
            "market_status": "unavailable",
            "error": "yfinance not installed",
            "indices": [],
            "tech_stocks": [],
        }
        if not is_mock_yf:
            cache_set("market", cache_key, result, ttl_seconds=None)
        return result

    indices: list[dict[str, Any]] = []
    market_status = "unknown"
    for cfg in _INDICES:
        quote = _get_quote(cfg["ticker"])
        if market_status == "unknown" and quote.get("market_status"):
            market_status = str(quote["market_status"]).lower()
        indices.append(
            {
                "ticker": cfg["ticker"],
                "name_cn": cfg["name_cn"],
                "change_pct": quote["change_pct"],
                "close": quote["close"],
                "prev_close": quote["prev_close"],
            }
        )

    tech_stocks: list[dict[str, Any]] = []
    for cfg in _TECH_STOCKS:
        quote = _get_quote(cfg["ticker"])
        tech_stocks.append(
            {
                "ticker": cfg["ticker"],
                "name_cn": cfg["name_cn"],
                "change_pct": quote["change_pct"],
                "close": quote["close"],
                "prev_close": quote["prev_close"],
                "a_share_sectors": _SECTOR_MAP.get(cfg["ticker"], []),
            }
        )

    result = {
        "fetched_at": fetched_at,
        "market_status": market_status,
        "indices": indices,
        "tech_stocks": tech_stocks,
    }
    if not is_mock_yf:
        cache_set("market", cache_key, result, ttl_seconds=None)
    return result
