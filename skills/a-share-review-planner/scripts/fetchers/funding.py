"""资金面抓取：北向净流入 + 主力净流入 Top20 + 趋势候选股资金详情。

依赖：可选 akshare>=1.15.0。
不可用时自动 fallback，返回 data_degraded=True，不阻断主流程。

接口说明（经实测验证）：
- 北向净流入：ak.stock_hsgt_fund_flow_summary_em()
    列名：资金方向（'北向'/'南向'）、资金净流入（亿）
    过滤 资金方向=='北向' 后对 资金净流入 求和（沪股通+深股通）。
- 主力净流入 Top20：ak.stock_individual_fund_flow_rank(indicator='今日')
    列名：代码、名称、今日主力净流入-净额（元）
    按 今日主力净流入-净额 降序取前20。
- 趋势候选股资金：复用上述 DataFrame 缓存，按代码过滤，零额外 API 调用。
"""

from __future__ import annotations

from typing import Any


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
) -> dict[str, Any]:
    return {
        "northbound_net": round(northbound_net, 3),
        "main_force_top20": top_rows[:20],
        "trend_candidates_funding": [],   # 采集时为空，由 collect_sentiment 补充
        "data_degraded": degraded,
    }


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


def _parse_main_force_rows(df: Any) -> list[dict[str, Any]]:
    """从 stock_individual_fund_flow_rank 返回值中提取全量排名数据。

    列名：代码、名称、今日主力净流入-净额（元）。
    返回按净流入降序排列的全量列表（含排名），同时写入模块缓存。
    """
    global _RANK_CACHE
    _RANK_CACHE = []

    if df is None or getattr(df, "empty", True):
        return []

    try:
        col_net = "今日主力净流入-净额"
        if col_net not in df.columns:
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
                all_rows.append({
                    "code": code,
                    "name": name,
                    "net_inflow": net_yi,
                    "rank": int(idx) + 1,
                })

        _RANK_CACHE = all_rows
        return all_rows[:20]
    except Exception:
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

    Args:
        date: 预留参数，底层接口默认取最新可得数据。

    Returns:
        {
            "northbound_net": float,              # 北向净流入（亿），正为流入
            "main_force_top20": [...],             # 主力净流入 Top20
            "trend_candidates_funding": [],        # 占位，由 collect_sentiment 补充
            "data_degraded": bool                  # True 表示数据获取失败
        }
    """
    _ = date
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return _build_funding_result(northbound_net=0.0, top_rows=[], degraded=True)

    north_net = 0.0
    top_rows: list[dict[str, Any]] = []

    try:
        north_df = ak.stock_hsgt_fund_flow_summary_em()
        north_net = _parse_northbound(north_df)
    except Exception:
        pass

    try:
        main_df = ak.stock_individual_fund_flow_rank(indicator="今日")
        top_rows = _parse_main_force_rows(main_df)
    except Exception:
        pass

    degraded = len(top_rows) == 0
    return _build_funding_result(northbound_net=north_net, top_rows=top_rows, degraded=degraded)


__all__ = ["fetch_funding", "fetch_funding_for_codes", "_build_funding_result"]
