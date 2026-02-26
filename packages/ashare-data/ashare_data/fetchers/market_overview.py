"""大盘云图与资金流向数据抓取模块。"""

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_json as core_http_json


def _http_json(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """纯标准库实现的 HTTP JSON 请求函数。"""
    cache_key = f"market_http|{method}|{url}|{body}"
    cached = cache_get("market", cache_key)
    if isinstance(cached, dict):
        return cached
    _headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        _headers.update(headers)
    data = core_http_json(url, method=method, payload=body, headers=_headers, timeout=15)
    cache_set("market", cache_key, data, ttl_seconds=1800)
    return data


# ---------------------------------------------------------------------------
# 公共 Headers
# ---------------------------------------------------------------------------

_JRJ_HEADERS = {
    "Origin": "https://summary.jrj.com.cn",
    "Referer": "https://summary.jrj.com.cn/",
}


# ---------------------------------------------------------------------------
# 核心抓取函数
# ---------------------------------------------------------------------------


def fetch_market_cloud() -> dict:
    """获取大盘云图数据（一级行业 → 二级行业 → 个股）。

    Returns:
        原始 market API 返回的完整 JSON dict。
    """
    return _http_json(
        "https://gateway.jrj.com/quot-dpyt/v1/market",
        method="POST",
        body={"mkt": 1},
        headers=_JRJ_HEADERS,
    )


def fetch_capital_flow() -> dict:
    """获取资金流向数据（个股净流入金额）。

    Returns:
        原始 hq API 返回的完整 JSON dict。
    """
    return _http_json(
        "https://gateway.jrj.com/quot-dpyt/v1/hq",
        method="POST",
        body={"column": "netin"},
        headers=_JRJ_HEADERS,
    )


def build_sector_summary(market_data: dict, flow_data: dict) -> list[dict]:
    """将大盘云图与资金流向数据合并，按一级行业聚合。

    Args:
        market_data: fetch_market_cloud() 的返回值。
        flow_data:   fetch_capital_flow() 的返回值。

    Returns:
        按 total_netin 降序排列的一级行业列表，每项包含：
        name, sid, scale, sub_sectors, total_netin,
        top_inflow_stocks, top_outflow_stocks。
    """
    indus_list = market_data.get("data", {}).get("indus", [])
    hqs = flow_data.get("data", {}).get("hqs", {})

    sectors: list[dict] = []

    for sector in indus_list:
        all_stocks: list[dict] = []
        sub_sectors: list[dict] = []

        for sub in sector.get("children", []):
            sub_netin = 0.0
            sub_count = 0
            for stock in sub.get("children", []):
                sid_key = str(stock.get("sid", ""))
                hq = hqs.get(sid_key, {})
                netin = hq.get("var", 0.0)
                sub_netin += netin
                sub_count += 1
                all_stocks.append(
                    {
                        "code": stock.get("code", ""),
                        "name": stock.get("name", ""),
                        "netin": netin,
                    }
                )
            sub_sectors.append(
                {
                    "name": sub.get("name", ""),
                    "sid": sub.get("sid", 0),
                    "stock_count": sub_count,
                    "total_netin": sub_netin,
                }
            )

        # 按净流入排序取 top5
        sorted_by_netin = sorted(all_stocks, key=lambda s: s["netin"], reverse=True)
        top_inflow = [s for s in sorted_by_netin[:5] if s["netin"] > 0]
        top_outflow = [s for s in sorted_by_netin[-5:] if s["netin"] < 0]
        # 流出按净流入升序（流出最多的排前面）
        top_outflow.sort(key=lambda s: s["netin"])

        total_netin = sum(s["netin"] for s in all_stocks)

        sectors.append(
            {
                "name": sector.get("name", ""),
                "sid": sector.get("sid", 0),
                "scale": sector.get("scale", 0.0),
                "sub_sectors": sub_sectors,
                "total_netin": total_netin,
                "top_inflow_stocks": top_inflow,
                "top_outflow_stocks": top_outflow,
            }
        )

    sectors.sort(key=lambda s: s["total_netin"], reverse=True)
    return sectors


def fetch_market_overview() -> dict:
    """一次调用获取完整的大盘概览数据。

    Returns:
        {"trade_date": "20260213", "sectors": [...]}
    """
    cached = cache_get("market", "market_overview_latest")
    if isinstance(cached, dict):
        return cached
    market_data = fetch_market_cloud()
    flow_data = fetch_capital_flow()

    trade_date = market_data.get("data", {}).get("td", "")

    result = {
        "trade_date": trade_date,
        "sectors": build_sector_summary(market_data, flow_data),
    }
    cache_set("market", "market_overview_latest", result, ttl_seconds=1800)
    return result


def fetch_market_sectors_top_n(n: int = 5) -> dict:
    """获取净流入前n和后n的板块摘要，用于 LLM 分析。

    每个板块只保留 name, total_netin, stock_count, top_inflow_stocks(前3),
    top_outflow_stocks(前3)，个股也精简到 name+netin。

    Returns:
        {
            "trade_date": "20260217",
            "top_inflow": [...],   # 前n板块
            "top_outflow": [...],  # 后n板块
            "sector_count": 31,
        }
    """
    overview = fetch_market_overview()
    sectors = overview.get("sectors", [])

    def _slim_sector(s: dict) -> dict:
        """精简单个板块，只保留 LLM 必需字段。"""
        return {
            "name": s["name"],
            "total_netin": s["total_netin"],
            "stock_count": sum(sub.get("stock_count", 0) for sub in s.get("sub_sectors", [])),
            "top_inflow_stocks": [
                {"name": st["name"], "netin": st["netin"]}
                for st in s.get("top_inflow_stocks", [])[:3]
            ],
            "top_outflow_stocks": [
                {"name": st["name"], "netin": st["netin"]}
                for st in s.get("top_outflow_stocks", [])[:3]
            ],
        }

    # sectors 已按 total_netin 降序排列
    top_inflow = [_slim_sector(s) for s in sectors[:n]]
    top_outflow = [_slim_sector(s) for s in sectors[-n:]]
    # 流出板块按净流入升序（流出最多的排前面）
    top_outflow.sort(key=lambda s: s["total_netin"])

    return {
        "trade_date": overview.get("trade_date", ""),
        "top_inflow": top_inflow,
        "top_outflow": top_outflow,
        "sector_count": len(sectors),
    }
