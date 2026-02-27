"""Market sentiment fetcher — THS limit-up/down count.

Purpose: Fetch today's limit-up and limit-down counts from Tonghuashun,
         classify danger level for market-wide risk gating.

Public API:
    fetch_market_sentiment() -> MarketSentiment
    MarketSentiment.danger_level: "green" / "yellow" / "red" / "unknown"
    MarketSentiment.market_open: True only when THS reports trading session is active
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime

from ashare_data.core.http_client import http_json

logger = logging.getLogger(__name__)

# THS limit-up pool: no cookie needed, requires User-Agent + millisecond timestamp (_)
# Response also contains limit_down_count — no separate limit-down API call needed.
_THS_URL = "http://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
_THS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Referer": "http://data.10jqka.com.cn/",
}
_THS_FIELDS = "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003"


@dataclass
class MarketSentiment:
    """当日市场情绪快照。

    danger_level 含义:
        "green"   -- 正常交易（跌停 < 30）
        "yellow"  -- 市场偏弱（跌停 30-79），信号门槛自动提高 15 分
        "red"     -- 市场高压（跌停 >= 80），中止扫描
        "unknown" -- 接口不可用，降级处理（不调整门槛）

    market_open: THS trade_status.id == "trading"，节假日/盘后为 False。
        False 时调用方应跳过扫描，避免基于昨日收盘价产生虚假信号。
    """

    limit_up: int = 0
    limit_down: int = 0
    danger_level: str = "unknown"
    market_open: bool = False


def fetch_market_sentiment(cookie: str | None = None) -> MarketSentiment:
    """调用同花顺涨停池接口，返回当日涨跌停计数与市场情绪等级。

    使用毫秒时间戳参数（_）绕过缓存，无需 Cookie。
    涨停池响应的 data.limit_down_count.today 字段同时包含跌停数据。

    Args:
        cookie: 可选，同花顺 Cookie（通常不需要）。

    Returns:
        MarketSentiment。接口不可用时返回 danger_level="unknown"。
    """
    headers = dict(_THS_HEADERS)
    if cookie:
        headers["Cookie"] = cookie

    today = datetime.now().strftime("%Y%m%d")  # THS 要求格式 YYYYMMDD，不含横线
    ts_ms = int(time.time() * 1000)
    url = (
        f"{_THS_URL}"
        f"?limit=1&field={_THS_FIELDS}"
        f"&page=1&filter=HS,GEM2STAR&order_field=330324&order_type=0"
        f"&date={today}&_={ts_ms}"
    )

    try:
        resp = http_json(url, headers=headers, timeout=10, retries=1)
    except Exception as exc:
        logger.warning("fetch_market_sentiment 请求失败: %s", exc)
        return MarketSentiment(danger_level="unknown")

    pool_data = resp.get("data") or {}
    if not isinstance(pool_data, dict):
        logger.warning("fetch_market_sentiment: 响应格式异常")
        return MarketSentiment(danger_level="unknown")

    # 交易状态：trade_status.id == "trading" 表示当前在交易时段
    # 节假日和盘后均为 "closed"，用于过滤非交易日的虚假信号
    trade_status_id = (pool_data.get("trade_status") or {}).get("id", "")
    market_open = trade_status_id == "trading"

    # 涨停总数：data.page.total
    limit_up = int((pool_data.get("page") or {}).get("total", 0))

    # 跌停数：data.limit_down_count.today（字段名可能是 num 或 count）
    ld_today = (pool_data.get("limit_down_count") or {}).get("today") or {}
    limit_down = int(
        ld_today.get("num", ld_today.get("count", ld_today.get("total", 0)))
    )

    if limit_up == 0 and limit_down == 0:
        logger.warning("市场情绪数据获取失败（涨跌停均为 0），降级为 unknown")
        return MarketSentiment(danger_level="unknown", market_open=market_open)

    if limit_down >= 80:
        danger_level = "red"
    elif limit_down >= 30:
        danger_level = "yellow"
    else:
        danger_level = "green"

    return MarketSentiment(
        limit_up=limit_up,
        limit_down=limit_down,
        danger_level=danger_level,
        market_open=market_open,
    )
