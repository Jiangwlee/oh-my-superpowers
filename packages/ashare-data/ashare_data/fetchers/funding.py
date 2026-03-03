"""资金面抓取：北向净流入 + 主力净流入 Top20 + 趋势候选股资金详情。

数据来源（均无需认证，直连可用）：
- 北向资金净流入：东方财富数据中心 datacenter-web.eastmoney.com
    reportName=RPT_MUTUAL_DEAL_HISTORY，过滤 MUTUAL_TYPE="006"（北向汇总），
    取最新一行 NET_DEAL_AMT ÷ 100 = 亿元
- 主力净流入排名：东方财富延迟行情推送 push2delay.eastmoney.com
    /api/qt/clist/get，indicator='3日' fid=f267，indicator='今日' fid=f62
    全市场 A 股，按净额降序，逐页翻取（每页100条）
"""

from __future__ import annotations

import json
import logging
import math
import urllib.parse
from datetime import datetime
from typing import Any

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_text, http_json
from ashare_data.core.utils import parse_float

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_NORTHBOUND_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_NORTHBOUND_PARAMS = {
    "reportName": "RPT_MUTUAL_DEAL_HISTORY",
    "columns": "MUTUAL_TYPE,TRADE_DATE,NET_DEAL_AMT",
    "filter": '(MUTUAL_TYPE="006")',
    "pageNumber": "1",
    "pageSize": "1",
    "sortTypes": "-1",
    "sortColumns": "TRADE_DATE",
    "source": "WEB",
    "client": "WEB",
}
_NORTHBOUND_HEADERS = {
    "Referer": "https://data.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/147.0",
}

_FUNDFLOW_URL = "https://push2delay.eastmoney.com/api/qt/clist/get"
_FUNDFLOW_UT = "b2884a393a59ad64002292a3e90d46a5"
_FUNDFLOW_FS = (
    "m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,"
    "m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2"
)
_FUNDFLOW_HEADERS = {
    "Referer": "https://data.eastmoney.com/zjlx/detail.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/147.0",
}

# indicator → (fid 排序字段, fields 列表, 净额字段)
_INDICATOR_CONFIG: dict[str, tuple[str, str, str]] = {
    "今日": (
        "f62",
        "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124",
        "f62",
    ),
    "3日": (
        "f267",
        "f12,f14,f2,f127,f267,f268,f269,f270,f271,f272,f273,f274,f275,f276,f257,f258,f124",
        "f267",
    ),
    "5日": (
        "f164",
        "f12,f14,f2,f109,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f257,f258,f124",
        "f164",
    ),
    "10日": (
        "f174",
        "f12,f14,f2,f160,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f260,f261,f124",
        "f174",
    ),
}

# ---------------------------------------------------------------------------
# 模块级缓存：fetch_funding() 调用后保存完整排名数据，供后续 cross-reference 使用
# ---------------------------------------------------------------------------

_RANK_CACHE: list[dict[str, Any]] = []  # [{code, name, net_inflow, rank}, ...]


def _build_funding_result(
    *,
    northbound_net: float,
    top_rows: list[dict[str, Any]],
    degraded: bool,
    funding_indicator: str = "3日",
    today_top20: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "northbound_net": round(northbound_net, 3),
        "main_force_top20": top_rows[:20],
        "funding_indicator": funding_indicator,
        "trend_candidates_funding": [],  # 采集时为空，由 collect_sentiment 补充
        "data_degraded": degraded,
    }
    if today_top20:
        result["today_top10"] = today_top20[:10]
    return result


# ---------------------------------------------------------------------------
# 兼容旧测试的 DataFrame 解析函数（保留，以防其他地方引用）
# ---------------------------------------------------------------------------


def _parse_northbound(df: Any) -> float:
    """从 DataFrame 中提取北向净流入（亿）。兼容旧路径，新路径直接用 HTTP。"""
    if df is None or getattr(df, "empty", True):
        return 0.0
    try:
        north = df[df["资金方向"] == "北向"]
        if north.empty:
            return 0.0
        return parse_float(north["资金净流入"].sum())
    except Exception:
        return 0.0


def _parse_main_force_rows(
    df: Any,
    indicator: str = "3日",
    *,
    update_cache: bool = True,
) -> list[dict[str, Any]]:
    """从 DataFrame 中提取全量排名数据。兼容旧测试路径，新路径直接用 HTTP。"""
    global _RANK_CACHE
    if update_cache:
        _RANK_CACHE = []

    if df is None or getattr(df, "empty", True):
        return []

    try:
        col_net = f"{indicator}主力净流入-净额"
        if col_net not in df.columns:
            logger.warning("列 %s 不存在，可用列: %s", col_net, list(df.columns))
            return []

        import pandas as pd  # type: ignore

        df = df.copy()
        df[col_net] = pd.to_numeric(df[col_net], errors="coerce")
        sorted_df = df.sort_values(col_net, ascending=False).reset_index(drop=True)

        all_rows: list[dict[str, Any]] = []
        for idx, series in sorted_df.iterrows():
            item = series.to_dict()
            code = str(item.get("代码") or "").strip()
            name = str(item.get("名称") or "").strip()
            net_yuan = parse_float(item.get(col_net, 0))
            net_yi = round(net_yuan / 1e8, 3)
            if code and name:
                all_rows.append(
                    {
                        "code": code,
                        "name": name,
                        "net_inflow": net_yi,
                        "rank": int(idx) + 1,
                    }
                )

        if update_cache:
            _RANK_CACHE = all_rows
        return all_rows
    except Exception:
        logger.exception("_parse_main_force_rows 出错 (indicator=%s)", indicator)
        return []


# ---------------------------------------------------------------------------
# 北向资金：datacenter-web.eastmoney.com
# ---------------------------------------------------------------------------


def _fetch_northbound_net() -> float:
    """获取北向资金今日净流入（沪股通+深股通合计，亿元）。

    接口：datacenter-web.eastmoney.com/api/data/v1/get
    reportName=RPT_MUTUAL_DEAL_HISTORY，过滤 MUTUAL_TYPE="006"（北向汇总行），
    取最新一行的 NET_DEAL_AMT ÷ 100 = 亿元。

    Returns:
        北向净流入（亿元），失败返回 0.0。
    """
    try:
        url = _NORTHBOUND_URL + "?" + urllib.parse.urlencode(_NORTHBOUND_PARAMS)
        body = http_text(url, headers=_NORTHBOUND_HEADERS, timeout=10)
        data = json.loads(body)
        rows = (data.get("result") or {}).get("data") or []
        if not rows:
            return 0.0
        val = rows[0].get("NET_DEAL_AMT")
        if val is None:
            return 0.0
        # NET_DEAL_AMT 原始单位：百万元（÷100 = 亿元）
        return round(float(val) / 100, 3)
    except Exception:
        logger.exception("北向资金采集失败")
        return 0.0


# ---------------------------------------------------------------------------
# 个股主力净流入排名：push2delay.eastmoney.com
# ---------------------------------------------------------------------------


def _fetch_fund_flow_rank(indicator: str = "3日") -> list[dict[str, Any]]:
    """获取全市场个股主力净流入排名（东方财富延迟行情接口）。

    Args:
        indicator: '今日' / '3日' / '5日' / '10日'

    Returns:
        按净流入降序的全量列表：
        [{"code": str, "name": str, "net_inflow": float(亿), "rank": int}, ...]
        失败时返回空列表。
    """
    cfg = _INDICATOR_CONFIG.get(indicator)
    if cfg is None:
        logger.warning("不支持的 indicator: %s", indicator)
        return []

    fid, fields, net_field = cfg
    global _RANK_CACHE

    all_rows: list[dict[str, Any]] = []
    try:
        # 第1页：获取总数量
        base_params = {
            "fid": fid,
            "po": "1",
            "pz": "100",
            "pn": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "ut": _FUNDFLOW_UT,
            "fs": _FUNDFLOW_FS,
            "fields": fields,
        }
        url = _FUNDFLOW_URL + "?" + urllib.parse.urlencode(base_params)
        body = http_text(url, headers=_FUNDFLOW_HEADERS, timeout=12)
        data = json.loads(body)
        diff = (data.get("data") or {}).get("diff") or []
        total = (data.get("data") or {}).get("total") or 0

        all_rows.extend(diff)

        # 翻页取剩余数据
        total_pages = math.ceil(total / 100)
        for pn in range(2, total_pages + 1):
            params = dict(base_params)
            params["pn"] = str(pn)
            url = _FUNDFLOW_URL + "?" + urllib.parse.urlencode(params)
            try:
                body = http_text(url, headers=_FUNDFLOW_HEADERS, timeout=12)
                page_data = json.loads(body)
                page_diff = (page_data.get("data") or {}).get("diff") or []
                all_rows.extend(page_diff)
            except Exception:
                logger.warning("第 %s 页翻页失败，已有 %s 条", pn, len(all_rows))
                break

    except Exception:
        logger.exception("主力净流入排名采集失败 (indicator=%s)", indicator)
        return []

    # 转换为标准格式
    result: list[dict[str, Any]] = []
    for rank, row in enumerate(all_rows, start=1):
        code = str(row.get("f12") or "").strip()
        name = str(row.get("f14") or "").strip()
        net_yuan = parse_float(row.get(net_field, 0))
        if code and name and net_yuan != 0.0:
            result.append(
                {
                    "code": code,
                    "name": name,
                    "net_inflow": round(net_yuan / 1e8, 3),
                    "rank": rank,
                }
            )

    return result


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------


def fetch_funding_for_codes(codes: list[str]) -> list[dict[str, Any]]:
    """从缓存中查询指定股票代码的主力净流入数据（零额外 API 调用）。

    必须在 fetch_funding() 调用之后使用，否则返回空列表。

    Args:
        codes: 6位股票代码列表，如 ["603163", "000738"]。

    Returns:
        [{"code": str, "name": str, "net_inflow": float, "rank": int}, ...]
        按 net_inflow 降序排列，不在排名中的代码不出现在结果里。
    """
    if not _RANK_CACHE or not codes:
        return []
    code_set = set(codes)
    matched = [row for row in _RANK_CACHE if row["code"] in code_set]
    return sorted(matched, key=lambda x: x["net_inflow"], reverse=True)


def fetch_funding(date: str | None = None) -> dict[str, Any]:
    """采集资金面数据，并缓存完整排名供 fetch_funding_for_codes() 使用。

    策略：主用 indicator='3日'（反映资金持续性，无盘前空数据问题），
    辅助采集 '今日'（盘前可能为空，仅在有数据时提供 today_top10）。

    Args:
        date: 预留参数，底层接口默认取最新可得数据。

    Returns:
        {
            "northbound_net": float,              # 北向净流入（亿），正为流入
            "main_force_top20": [...],             # 3日主力净流入 Top20
            "funding_indicator": "3日",            # 主排名所用的时间窗口
            "today_top10": [...] | absent,         # 今日主力净流入 Top10（盘前为空时不存在）
            "trend_candidates_funding": [],        # 占位，由 collect_sentiment 补充
            "data_degraded": bool                  # True 表示主数据获取失败
        }
    """
    cache_day = date or datetime.now().strftime("%Y-%m-%d")
    cache_key = f"funding_{cache_day}"
    cached = cache_get("funding", cache_key)
    if isinstance(cached, dict):
        main_force = cached.get("main_force_top20")
        if isinstance(main_force, list):
            global _RANK_CACHE
            _RANK_CACHE = [
                row
                for row in main_force
                if isinstance(row, dict) and row.get("code") and row.get("name")
            ]
        return cached

    # 北向资金
    north_net = _fetch_northbound_net()

    # 主指标：3日主力净流入排名（全量，写入缓存）
    top_rows = _fetch_fund_flow_rank(indicator="3日")
    _RANK_CACHE = top_rows  # type: ignore[assignment]

    # 辅助：今日排名（盘前可能为空，不写全局缓存）
    today_rows: list[dict[str, Any]] = []
    try:
        today_rows = _fetch_fund_flow_rank(indicator="今日")
    except Exception:
        pass  # 盘前为空是正常的，静默处理

    degraded = len(top_rows) == 0
    result = _build_funding_result(
        northbound_net=north_net,
        top_rows=top_rows,
        degraded=degraded,
        funding_indicator="3日",
        today_top20=today_rows[:10] if today_rows else None,
    )
    cache_set("funding", cache_key, result, ttl_seconds=None)
    return result


__all__ = [
    "fetch_funding",
    "fetch_funding_for_codes",
    "_build_funding_result",
    "_parse_northbound",
    "_parse_main_force_rows",
]
