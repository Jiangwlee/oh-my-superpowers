"""获取 A 股最近交易日期。"""

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_json

_TRADE_DATE_URL = "https://gateway.jrj.com/quot-feed/tradedate"

_HEADERS = {
    "Origin": "https://summary.jrj.com.cn",
    "Referer": "https://summary.jrj.com.cn/",
}


def fetch_trade_date() -> str:
    """返回最近交易日期，格式 YYYYMMDD。

    调用金融界网关接口 POST /quot-feed/tradedate 获取数据。

    Returns
    -------
    str
        例如 ``"20260217"``。

    Raises
    ------
    RuntimeError
        接口返回异常或解析失败时抛出。
    """
    cached = cache_get("kline", "trade_date_latest")
    if isinstance(cached, str) and len(cached) == 8:
        return cached
    resp = http_json(
        url=_TRADE_DATE_URL,
        method="POST",
        headers=_HEADERS,
    )

    # 响应示例: {"code": 20000, "msg": "成功", "data": {"mkt_sts": 1, "td": 20260213}}
    try:
        trade_date = str(resp["data"]["td"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"解析 tradedate 响应失败: {resp}") from exc

    cache_set("kline", "trade_date_latest", trade_date, ttl_seconds=1800)
    return trade_date
