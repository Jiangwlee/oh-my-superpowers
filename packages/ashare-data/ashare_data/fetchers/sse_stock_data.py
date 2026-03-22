"""上交所股票数据抓取模块。

说明
----
- 数据源来自上交所官网股票数据页背后的 `query.sse.com.cn/commonQuery.do`
- 页面通过 JSONP 方式加载数据，因此这里使用 `http_text` + JSONP 解析
- 当前覆盖三个页面：
  1. 股票成交概况 / 每日概况
  2. 股票数据 / 统计数据
  3. 活跃股排名 / 主板活跃股排名

公共约定
--------
- 所有日期参数均使用 `YYYY-MM-DD`
- 请求失败或响应异常时返回空结果，不向上抛异常
- 输出以结构化 dict 为主，保留上交所原始字段，便于后续扩展
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlencode

from ashare_data.core.http_client import http_text

logger = logging.getLogger(__name__)

_SSE_QUERY_URL = "https://query.sse.com.cn/commonQuery.do"
_JSONP_CALLBACK = "jsonpCallback"
_OVERVIEW_DAY_REFERER = "https://www.sse.com.cn/market/stockdata/overview/day/"
_STATISTIC_REFERER = "https://www.sse.com.cn/market/stockdata/statistic/"
_ACTIVITY_MAIN_REFERER = "https://www.sse.com.cn/market/stockdata/activity/main/"
_OVERVIEW_DAY_PRODUCT_CODE = "01,02,03,11,17"
_STATISTIC_PRODUCT_NAME = "股票,主板,科创板"
_ACTIVITY_MAIN_SORT_FIELDS = {
    "TRADE_VOL_DESC",
    "TRADE_AMT_DESC",
    "CHANGE_RATIO_DESC",
    "CHANGE_RATIO_ASC",
    "QJZF_DESC",
    "TO_RATE_DESC",
}


def _parse_jsonp(payload: str) -> dict[str, Any]:
    """解析 JSONP 为 dict。"""
    body = payload.strip()
    left = body.find("(")
    right = body.rfind(")")
    if left == -1 or right == -1 or left >= right:
        raise ValueError("invalid JSONP payload")
    return json.loads(body[left + 1 : right])


def _fetch_sse_query(params: dict[str, Any], referer: str) -> dict[str, Any]:
    """执行上交所 JSONP 查询。"""
    query = {"jsonCallBack": _JSONP_CALLBACK}
    query.update(params)
    url = f"{_SSE_QUERY_URL}?{urlencode(query)}"
    headers = {
        "Accept": "*/*",
        "Referer": referer,
        "User-Agent": "Mozilla/5.0",
    }
    payload = http_text(url, headers=headers, timeout=15, retries=2)
    return _parse_jsonp(payload)


def fetch_sse_overview_day(search_date: str = "") -> dict[str, Any]:
    """抓取上交所股票成交概况的每日概况。

    Args:
        search_date: 查询日期，格式 `YYYY-MM-DD`。为空时取上交所接口默认最近交易日。

    Returns:
        {
            "trade_date": "20260320",
            "rows": [...],
            "by_product_code": {"17": {...}, ...},
        }
    """
    params = {
        "sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C",
        "PRODUCT_CODE": _OVERVIEW_DAY_PRODUCT_CODE,
        "type": "inParams",
        "SEARCH_DATE": search_date,
    }
    try:
        resp = _fetch_sse_query(params, referer=_OVERVIEW_DAY_REFERER)
    except Exception as exc:
        logger.exception("fetch_sse_overview_day 请求失败: %s", exc)
        return {"trade_date": "", "rows": [], "by_product_code": {}}

    rows = resp.get("result") or []
    if not isinstance(rows, list):
        return {"trade_date": "", "rows": [], "by_product_code": {}}
    trade_date = str(rows[0].get("TRADE_DATE", "")) if rows else ""
    by_product_code = {
        str(row.get("PRODUCT_CODE", "")): row for row in rows if isinstance(row, dict)
    }
    return {
        "trade_date": trade_date,
        "rows": rows,
        "by_product_code": by_product_code,
    }


def fetch_sse_statistic(trade_date: str = "") -> dict[str, Any]:
    """抓取上交所股票数据总貌。

    Args:
        trade_date: 查询日期，格式 `YYYY-MM-DD`。为空时取最近交易日。

    Returns:
        {
            "trade_date": "20260320",
            "rows": [...],
            "by_product_name": {"股票": {...}, "主板": {...}, "科创板": {...}},
        }
    """
    params = {
        "sqlId": "COMMON_SSE_SJ_GPSJ_GPSJZM_TJSJ_L",
        "PRODUCT_NAME": _STATISTIC_PRODUCT_NAME,
        "type": "inParams",
        "TRADE_DATE": trade_date,
    }
    try:
        resp = _fetch_sse_query(params, referer=_STATISTIC_REFERER)
    except Exception as exc:
        logger.exception("fetch_sse_statistic 请求失败: %s", exc)
        return {"trade_date": "", "rows": [], "by_product_name": {}}

    rows = resp.get("result") or []
    if not isinstance(rows, list):
        return {"trade_date": "", "rows": [], "by_product_name": {}}
    resolved_trade_date = str(rows[0].get("TRADE_DATE", "")) if rows else ""
    by_product_name = {
        str(row.get("PRODUCT_NAME", "")): row for row in rows if isinstance(row, dict)
    }
    return {
        "trade_date": resolved_trade_date,
        "rows": rows,
        "by_product_name": by_product_name,
    }


def fetch_sse_activity_main(
    trade_date: str = "",
    *,
    sort_by: str = "TRADE_VOL_DESC",
    page_size: int = 20,
) -> dict[str, Any]:
    """抓取上交所主板活跃股排名。

    Args:
        trade_date: 查询日期，格式 `YYYY-MM-DD`。为空时取最近交易日。
        sort_by: 排序字段，仅允许页面白名单字段。
        page_size: 返回条数，默认 20。

    Returns:
        {
            "trade_date": "20260320",
            "sort_by": "TRADE_VOL_DESC",
            "rows": [...],
            "total": 20,
            "page_size": 20,
        }
    """
    if sort_by not in _ACTIVITY_MAIN_SORT_FIELDS:
        raise ValueError(f"unsupported sort_by: {sort_by}")

    params: dict[str, Any] = {
        "isPagination": "true",
        "pageHelp.pageSize": page_size,
        "pageHelp.cacheSize": 1,
        "sqlId": "COMMON_SSE_SJ_GPSJ_HYGPM_L",
        "LIST_BOARD": 1,
        "TRADE_DATE": trade_date,
        sort_by: 1,
    }
    try:
        resp = _fetch_sse_query(params, referer=_ACTIVITY_MAIN_REFERER)
    except Exception as exc:
        logger.exception("fetch_sse_activity_main 请求失败: %s", exc)
        return {
            "trade_date": "",
            "sort_by": sort_by,
            "rows": [],
            "total": 0,
            "page_size": page_size,
        }

    rows = resp.get("result") or []
    if not isinstance(rows, list):
        rows = []
    page_help = resp.get("pageHelp") or {}
    if not isinstance(page_help, dict):
        page_help = {}
    resolved_trade_date = str(rows[0].get("TRADE_DATE", "")) if rows else ""
    total = int(page_help.get("total", len(rows) or 0))
    return {
        "trade_date": resolved_trade_date,
        "sort_by": sort_by,
        "rows": rows,
        "total": total,
        "page_size": int(page_help.get("pageSize", page_size) or page_size),
    }

