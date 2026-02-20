"""资金面抓取：北向净流入 + 主力净流入 Top20。"""

from __future__ import annotations

from typing import Any


def _to_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _extract_first_numeric(row: dict[str, Any], preferred_keys: list[str]) -> float:
    for key in preferred_keys:
        if key in row:
            return _to_float(row.get(key))
    for value in row.values():
        num = _to_float(value)
        if num != 0.0:
            return num
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
        "data_degraded": degraded,
    }


def _parse_northbound(df: Any) -> float:
    if df is None or getattr(df, "empty", True):
        return 0.0
    row = df.iloc[-1].to_dict()
    return _extract_first_numeric(
        row,
        [
            "净流入(亿)",
            "净流入",
            "当日净流入",
            "北向资金净流入",
        ],
    )


def _parse_main_force_rows(df: Any) -> list[dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []

    rows: list[dict[str, Any]] = []
    for _, series in df.head(20).iterrows():
        item = series.to_dict()
        code = str(item.get("代码") or item.get("stock_code") or item.get("证券代码") or "").strip()
        name = str(item.get("名称") or item.get("name") or item.get("证券简称") or "").strip()
        net_inflow = _extract_first_numeric(item, ["主力净流入-净额", "主力净流入", "净流入", "net_inflow"])
        if code and name:
            rows.append({"code": code, "name": name, "net_inflow": round(net_inflow, 3)})
    return rows


def fetch_funding(date: str | None = None) -> dict[str, Any]:
    """采集资金面数据。

    date 参数当前仅作为预留，底层接口默认取最新可得数据。
    """
    _ = date
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return _build_funding_result(northbound_net=0.0, top_rows=[], degraded=True)

    try:
        north_df = None
        for fn_name in ("stock_hsgt_north_net_flow_in_em", "stock_hsgt_hist_em"):
            fn = getattr(ak, fn_name, None)
            if callable(fn):
                try:
                    north_df = fn()
                    if north_df is not None:
                        break
                except Exception:
                    continue

        main_df = None
        for fn_name in ("stock_main_fund_flow", "stock_fund_flow_individual", "stock_individual_fund_flow_rank"):
            fn = getattr(ak, fn_name, None)
            if callable(fn):
                try:
                    main_df = fn()
                    if main_df is not None:
                        break
                except Exception:
                    continue

        northbound_net = _parse_northbound(north_df)
        top_rows = _parse_main_force_rows(main_df)
        degraded = len(top_rows) == 0
        return _build_funding_result(northbound_net=northbound_net, top_rows=top_rows, degraded=degraded)
    except Exception:
        return _build_funding_result(northbound_net=0.0, top_rows=[], degraded=True)


__all__ = ["fetch_funding", "_build_funding_result"]
