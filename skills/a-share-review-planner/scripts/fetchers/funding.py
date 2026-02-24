"""资金面抓取：北向净流入 + 主力净流入 Top20 + 趋势候选股资金详情。

依赖：可选 akshare>=1.15.0。
不可用时自动 fallback，返回 data_degraded=True，不阻断主流程。

接口说明（经实测验证）：
- 北向净流入：ak.stock_hsgt_fund_flow_summary_em()
    列名：资金方向（'北向'/'南向'）、资金净流入（亿）
    过滤 资金方向=='北向' 后对 资金净流入 求和（沪股通+深股通）。
- 主力净流入排名：ak.stock_individual_fund_flow_rank(indicator=...)
    indicator 可选：'今日' / '3日' / '5日' / '10日'
    列名模式：{indicator}主力净流入-净额（元）
    主用 '3日' 排名（反映资金持续性，且无盘前空数据问题），
    辅助采集 '今日' 作为当日实时参考（盘前可能为空）。
- 趋势候选股资金：复用上述 DataFrame 缓存，按代码过滤，零额外 API 调用。
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 模块级缓存：fetch_funding() 调用后保存完整排名数据，供后续 cross-reference 使用
# ---------------------------------------------------------------------------

_RANK_CACHE: list[dict[str, Any]] = []  # [{code, name, net_inflow, rank}, ...]


def _to_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


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


def _parse_northbound(df: Any) -> float:
    """从 stock_hsgt_fund_flow_summary_em 返回值中提取北向净流入（亿）。

    过滤 资金方向=='北向' 后对 资金净流入 列求和（沪股通+深股通）。
    """
    if df is None or getattr(df, "empty", True):
        return 0.0
    try:
        north = df[df["资金方向"] == "北向"]
        if north.empty:
            return 0.0
        return _to_float(north["资金净流入"].sum())
    except Exception:
        return 0.0


def _parse_main_force_rows(
    df: Any,
    indicator: str = "3日",
    *,
    update_cache: bool = True,
) -> list[dict[str, Any]]:
    """从 stock_individual_fund_flow_rank 返回值中提取全量排名数据。

    Args:
        df: akshare 返回的 DataFrame。
        indicator: 数据时间窗口，决定列名前缀（'今日'/'3日'/'5日'/'10日'）。
        update_cache: 是否更新模块级 _RANK_CACHE（仅主指标应设为 True）。

    Returns:
        按净流入降序排列的全量列表（含排名），同时可选写入模块缓存。
    """
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
            net_yuan = _to_float(item.get(col_net, 0))
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
    _ = date
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return _build_funding_result(northbound_net=0.0, top_rows=[], degraded=True)

    north_net = 0.0
    top_rows: list[dict[str, Any]] = []
    today_rows: list[dict[str, Any]] = []

    # 北向资金
    try:
        north_df = ak.stock_hsgt_fund_flow_summary_em()
        north_net = _parse_northbound(north_df)
    except Exception:
        logger.exception("北向资金采集失败")

    # 主指标：3日主力净流入排名
    try:
        main_df = ak.stock_individual_fund_flow_rank(indicator="3日")
        top_rows = _parse_main_force_rows(main_df, indicator="3日", update_cache=True)
    except Exception:
        logger.exception("3日主力净流入排名采集失败")

    # 辅助：今日主力净流入（盘前可能为空，不影响主流程）
    try:
        today_df = ak.stock_individual_fund_flow_rank(indicator="今日")
        today_rows = _parse_main_force_rows(
            today_df,
            indicator="今日",
            update_cache=False,
        )
    except Exception:
        pass  # 盘前为空是正常的，静默处理

    degraded = len(top_rows) == 0
    return _build_funding_result(
        northbound_net=north_net,
        top_rows=top_rows,
        degraded=degraded,
        funding_indicator="3日",
        today_top20=today_rows[:10] if today_rows else None,
    )


__all__ = ["fetch_funding", "fetch_funding_for_codes", "_build_funding_result"]
