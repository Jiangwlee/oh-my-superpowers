"""A股趋势扫描模块 — 人气榜拉取、K线分析、趋势评分。

数据通道:
1) 东方财富人气排名 (xuangu + fallback)
2) 同花顺涨停/板块快照
3) 金融界日K线

所有 HTTP 请求复用 scripts.core.http_client.http_json。
"""

from __future__ import annotations

import bisect
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_json
from ashare_data.core.utils import norm_price

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _now_ymd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _to_plain_code(sc: str) -> str:
    sc = (sc or "").upper().strip()
    if sc.startswith(("SZ", "SH", "BJ")):
        return sc[2:]
    return sc


def _to_secid(sc: str) -> str:
    sc = (sc or "").upper().strip()
    if sc.startswith("SH"):
        return f"1.{sc[2:]}"
    if sc.startswith(("SZ", "BJ")):
        return f"0.{sc[2:]}"
    code = _to_plain_code(sc)
    return f"1.{code}" if code.startswith("6") else f"0.{code}"


def _to_jrj_security_id(code: str) -> str:
    return f"1{code}" if code.startswith("6") else f"2{code}"


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = den = 0.0
    for i, y in enumerate(values):
        dx = i - x_mean
        num += dx * (y - y_mean)
        den += dx * dx
    return 0.0 if den == 0 else num / den


def _window_slope_pct_per_day(closes: list[float], window: int) -> float:
    if len(closes) < window or closes[-window] <= 0:
        return 0.0
    slope = _linear_slope(closes[-window:])
    return slope / closes[-window] * 100.0


def _decile_score(
    values: list[float], value: float, higher_better: bool = True
) -> float:
    if not values:
        return 5.0
    if higher_better:
        arr = sorted(values)
        pos = bisect.bisect_right(arr, value)
    else:
        arr = sorted(-x for x in values)
        pos = bisect.bisect_right(arr, -value)
    return float(max(1, min(10, math.ceil(pos / len(values) * 10))))


def _to_star(total_score_100: float) -> int:
    if total_score_100 >= 85:
        return 5
    if total_score_100 >= 75:
        return 4
    if total_score_100 >= 65:
        return 3
    if total_score_100 >= 55:
        return 2
    return 1


def _format_star_emoji(star_rating: int) -> str:
    stars = max(1, min(5, int(star_rating)))
    return "\u2b50" * stars + "\u26aa" * (5 - stars)


# ---------------------------------------------------------------------------
# TrendResult dataclass
# ---------------------------------------------------------------------------


@dataclass
class TrendResult:
    code: str = ""
    name: str = ""
    sc: str = ""
    rank: int = 0
    source: str = ""
    bars_30: int = 0
    bars_60: int = 0
    red_days: int = 0
    red_ratio: float = 0.0
    holding_experience: str = "\u8f83\u5dee"
    gain_30_pct: float = 0.0
    gain_60_pct: float = 0.0
    up_day_ratio: float = 0.0
    slope_3_pct_per_day: float = 0.0
    slope_5_pct_per_day: float = 0.0
    slope_10_pct_per_day: float = 0.0
    slope_30: float = 0.0
    slope_30_pct_per_day: float = 0.0
    ma5_below_count: int = 0
    ma5_current_below_streak: int = 0
    ma5_max_below_streak: int = 0
    ma5_above_count: int = 0
    ma10_below_count: int = 0
    ma10_current_below_streak: int = 0
    ma10_max_below_streak: int = 0
    ma10_above_count: int = 0
    ma10_above_ma20_days_20: int = 0
    ma10_above_ma20_ratio_20: float = 0.0
    ma10_rising_10d: bool = False
    ma10_rising_streak: int = 0
    ma20_below_count: int = 0
    ma20_current_below_streak: int = 0
    ma20_max_below_streak: int = 0
    ma20_above_count: int = 0
    ma20_rising_20d: bool = False
    ma20_up_days_20: int = 0
    ma20_rising_streak: int = 0
    attack_gain8_days: int = 0
    attack_gain8_ratio: float = 0.0
    defense_drop5_days: int = 0
    defense_safe_ratio: float = 0.0
    ma_support_penalty: float = 9999.0
    score_trend_10: float = 0.0
    score_support_10: float = 0.0
    score_risk_10: float = 0.0
    score_robust_10: float = 0.0
    score_emotion_10: float = 1.0
    score_total_100: float = 0.0
    star_rating: int = 1
    emotion_level: int = 1
    emotion_label: str = "\u60c5\u7eea\u4e0d\u4f73"
    emotion_color: str = "\u26aa"
    emotion_reason: str = ""
    trade_signal: str = "\u89c2\u5bdf"
    trade_signal_reason: str = ""
    ma5_dist_pct: float = 0.0   # (last_close - ma5) / ma5 * 100
    ma10_dist_pct: float = 0.0  # (last_close - ma10) / ma10 * 100
    is_uptrend: bool = False
    reason: str = ""

    @classmethod
    def empty(
        cls, *, code: str, name: str, sc: str, rank: int, source: str, reason: str
    ) -> TrendResult:
        return cls(code=code, name=name, sc=sc, rank=rank, source=source, reason=reason)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 东方财富人气榜
# ---------------------------------------------------------------------------


def fetch_eastmoney_top_rank_xuangu(
    top_n: int = 1000, timeout: float = 15.0
) -> list[dict[str, Any]]:
    cache_key = f"xuangu_top_rank|top_n={top_n}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, list):
        return cached
    top_n = max(1, min(4000, top_n))
    page = 1
    page_size = 50
    rows: list[dict[str, Any]] = []

    while True:
        url = "https://data.eastmoney.com/dataapi/xuangu/list?" + urlencode(
            {
                "st": "CHANGE_RATE",
                "sr": "-1",
                "ps": str(page_size),
                "p": str(page),
                "sty": (
                    "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NEW_PRICE,CHANGE_RATE,"
                    "VOLUME_RATIO,HIGH_PRICE,LOW_PRICE,PRE_CLOSE_PRICE,VOLUME,DEAL_AMOUNT,"
                    "TURNOVERRATE,POPULARITY_RANK"
                ),
                "filter": f"(POPULARITY_RANK>0)(POPULARITY_RANK<={top_n})",
                "source": "SELECT_SECURITIES",
                "client": "WEB",
            }
        )
        data = http_json(url, timeout=timeout)
        result = data.get("result") if isinstance(data, dict) else None
        page_rows = result.get("data", []) if isinstance(result, dict) else []
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(rows) >= top_n or not result.get("nextpage"):
            break
        page += 1

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in rows:
        rank = int(item.get("POPULARITY_RANK", 0) or 0)
        if rank <= 0 or rank > top_n:
            continue
        secucode = str(item.get("SECUCODE", "")).upper()
        code = str(item.get("SECURITY_CODE", "")).strip()
        name = str(item.get("SECURITY_NAME_ABBR", "")).strip() or "\u672a\u77e5"

        sc = ""
        if secucode and "." in secucode:
            c, mkt = secucode.split(".", 1)
            if mkt == "SH":
                sc = f"SH{c}"
            elif mkt in ("SZ", "BJ"):
                sc = f"{mkt}{c}"
        if not sc:
            sc = f"SH{code}" if code.startswith("6") else f"SZ{code}"
        if not code:
            code = _to_plain_code(sc)
        if not code or sc in seen:
            continue
        seen.add(sc)
        out.append(
            {
                "sc": sc,
                "code": code,
                "name": name,
                "rank": rank,
                "rank_change": 0,
                "from": "eastmoney_xuangu",
                "guba_link": f"https://guba.eastmoney.com/list,{code}.html",
            }
        )
    out.sort(key=lambda x: x["rank"])
    result = out[:top_n]
    cache_set("eastmoney", cache_key, result, ttl_seconds=1800)
    return result


def _fetch_eastmoney_current_rank(
    limit: int = 1000, timeout: float = 15.0
) -> list[dict[str, Any]]:
    cache_key = f"current_rank|limit={limit}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, list):
        return cached
    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    page_size = min(100, max(1, int(limit)))
    page_no = 1
    result: list[dict[str, Any]] = []
    while len(result) < limit:
        payload = {
            "appId": "appId01",
            "globalId": "786e4c21-70dc-435a-93bb-38",
            "marketType": "",
            "pageNo": page_no,
            "pageSize": page_size,
        }
        data = (
            http_json(url, method="POST", payload=payload, timeout=timeout).get("data", [])
            or []
        )
        if not isinstance(data, list) or not data:
            break
        result.extend(data)
        if len(data) < page_size:
            break
        page_no += 1
    result = result[:limit]
    cache_set("eastmoney", cache_key, result, ttl_seconds=1800)
    return result


def _fetch_eastmoney_names(sc_list: list[str], timeout: float = 15.0) -> dict[str, str]:
    cache_key = "names|" + ",".join(sorted(sc_list))
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, dict):
        return {str(k): str(v) for k, v in cached.items()}
    out: dict[str, str] = {}
    for i in range(0, len(sc_list), 50):
        batch = sc_list[i : i + 50]
        secids = ",".join(_to_secid(sc) for sc in batch)
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get?" + urlencode(
            {
                "fltt": "2",
                "np": "3",
                "ut": "a79f54e3d4c8d44e494efb8f748db291",
                "invt": "2",
                "secids": secids,
                "fields": "f12,f13,f14",
            }
        )
        try:
            data = http_json(url, timeout=timeout)
            for row in (data.get("data", {}) or {}).get("diff", []) or []:
                code = str(row.get("f12", "")).strip()
                name = str(row.get("f14", "")).strip()
                mkt = int(row.get("f13", 0) or 0)
                prefix = "SH" if mkt == 1 else "SZ"
                if code and name:
                    out[f"{prefix}{code}"] = name
        except Exception:
            continue
    cache_set("eastmoney", cache_key, out, ttl_seconds=1800)
    return out


def fetch_eastmoney_popularity_rank(
    top_n: int = 1000, timeout: float = 15.0
) -> list[dict[str, Any]]:
    """获取东方财富个股人气榜前N名，支持最多 4000 只。"""
    top_n = max(1, min(4000, top_n))
    try:
        top = fetch_eastmoney_top_rank_xuangu(top_n=top_n, timeout=timeout)
        if top:
            return top
    except Exception:
        pass

    current = _fetch_eastmoney_current_rank(limit=top_n, timeout=timeout)
    current.sort(key=lambda x: int(x.get("rk", 10**9)))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in current:
        sc = str(item.get("sc", "")).upper()
        if not sc or sc in seen:
            continue
        seen.add(sc)
        out.append(
            {
                "sc": sc,
                "code": _to_plain_code(sc),
                "rank": int(item.get("rk", 0) or 0),
                "rank_change": int(item.get("rc", 0) or 0),
                "from": "eastmoney_current",
            }
        )
        if len(out) >= top_n:
            break

    names = _fetch_eastmoney_names([x["sc"] for x in out], timeout=timeout)
    for x in out:
        x["name"] = names.get(x["sc"], "\u672a\u77e5")
        x["guba_link"] = f"https://guba.eastmoney.com/list,{x['code']}.html"
    return out


# ---------------------------------------------------------------------------
# 同花顺涨停快照
# ---------------------------------------------------------------------------


def fetch_ths_snapshot(
    end_date: str | None = None, timeout: float = 15.0
) -> dict[str, Any]:
    cache_date = end_date or _now_ymd()
    cache_key = f"snapshot|{cache_date}"
    cached = cache_get("ths", cache_key)
    if isinstance(cached, dict):
        return cached
    if not end_date:
        end_date = _now_ymd()
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    ths_headers = {"Referer": "https://data.10jqka.com.cn/"}

    for delta in range(0, 35):
        d = (end_dt - timedelta(days=delta)).strftime("%Y%m%d")
        u1 = (
            "https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up?"
            + urlencode({"filter": "HS,GEM2STAR", "date": d})
        )
        u2 = "http://data.10jqka.com.cn/dataapi/limit_up/block_top?" + urlencode(
            {"filter": "HS,GEM2STAR", "date": d}
        )
        try:
            c1 = http_json(u1, headers=ths_headers, timeout=timeout)
            c2 = http_json(u2, headers=ths_headers, timeout=timeout)
            lu = c1.get("data", []) or []
            bt = c2.get("data", []) or []
            # 只在有实际数据时返回（假期 API 返回 status=0 但数据为空）
            if (c1.get("status_code") == 0 or c2.get("status_code") == 0) and (
                lu or bt
            ):
                result = {"date": d, "continuous_limit_up": lu, "block_top": bt}
                cache_set("ths", cache_key, result, ttl_seconds=1800)
                return result
        except Exception:
            continue

    result = {"date": None, "continuous_limit_up": [], "block_top": []}
    cache_set("ths", cache_key, result, ttl_seconds=1800)
    return result


# ---------------------------------------------------------------------------
# 同花顺涨停历史（最近 N 个交易日）
# ---------------------------------------------------------------------------


def fetch_ths_history(
    days: int = 5, end_date: str | None = None, timeout: float = 15.0
) -> list[dict]:
    """收集最近 days 个有效交易日的涨停快照，按日期升序排列。

    每日数据精简（去除冗长的 reason_info），只保留：
    - continuous_limit_up: code/name/continue_num/reason_type/change_rate/change_tag
    - block_top: name/limit_up_count/stock_list（前5只，同上精简）
    """
    cache_key = f"history|days={days}|end={end_date or _now_ymd()}"
    cached = cache_get("ths", cache_key)
    if isinstance(cached, list):
        return cached
    if not end_date:
        end_date = _now_ymd()
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    ths_headers = {"Referer": "https://data.10jqka.com.cn/"}

    _STOCK_KEEP = {
        "code",
        "name",
        "continue_num",
        "reason_type",
        "change_rate",
        "change_tag",
    }

    def _slim_block_stocks(stocks: list) -> list:
        """精简板块内个股字段（block_top.stock_list 为平铺结构）"""
        return [{k: v for k, v in s.items() if k in _STOCK_KEEP} for s in stocks]

    def _flatten_lu(groups: list) -> list:
        """展开连板天梯分组（{height, code_list} -> 个股列表）"""
        out = []
        for grp in groups:
            height = grp.get("height", 1)
            for s in grp.get("code_list") or []:
                out.append(
                    {
                        "code": s.get("code"),
                        "name": s.get("name"),
                        "continue_num": height,
                    }
                )
        return out

    history: list[dict] = []
    delta = 0
    while len(history) < days and delta < 60:
        d = (end_dt - timedelta(days=delta)).strftime("%Y%m%d")
        u1 = (
            "https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up?"
            + urlencode({"filter": "HS,GEM2STAR", "date": d})
        )
        u2 = "http://data.10jqka.com.cn/dataapi/limit_up/block_top?" + urlencode(
            {"filter": "HS,GEM2STAR", "date": d}
        )
        try:
            c1 = http_json(u1, headers=ths_headers, timeout=timeout)
            c2 = http_json(u2, headers=ths_headers, timeout=timeout)
            lu = c1.get("data", []) or []
            bt = c2.get("data", []) or []
            if (c1.get("status_code") == 0 or c2.get("status_code") == 0) and (
                lu or bt
            ):
                slim_bt = [
                    {
                        "name": blk.get("name"),
                        "limit_up_num": blk.get("limit_up_num"),
                        "change": blk.get("change"),
                        "stock_list": _slim_block_stocks(
                            (blk.get("stock_list") or [])[:5]
                        ),
                    }
                    for blk in bt
                ]
                history.append(
                    {
                        "date": d,
                        "continuous_limit_up": _flatten_lu(lu),
                        "block_top": slim_bt,
                    }
                )
        except Exception:
            pass
        delta += 1

    history.reverse()  # 升序（最旧在前）
    cache_set("ths", cache_key, history, ttl_seconds=1800)
    return history


# ---------------------------------------------------------------------------
# 同花顺涨停报告（Markdown 格式）
# ---------------------------------------------------------------------------


def format_ths_md(snapshot: dict, history: list[dict]) -> str:
    """将快照 + 历史数据格式化为可读 Markdown 报告。

    Parameters
    ----------
    snapshot : dict
        fetch_ths_snapshot() 的返回值（最新交易日完整数据）。
    history : list[dict]
        fetch_ths_history() 的返回值（近5日精简数据，升序）。
    """
    _TAG_ZH = {
        "FIRST_LIMIT": "首板",
        "LIMIT_BACK": "连板",
        "OPEN_LIMIT": "开板",
        "HIGH_LIMIT": "高位板",
    }

    def _tag(raw: str | None) -> str:
        return _TAG_ZH.get(raw or "", raw or "—")

    def _flatten_snap_lu(groups: list) -> list:
        """展开 snapshot 的连板天梯分组"""
        out = []
        for grp in groups:
            height = grp.get("height", 1)
            for s in grp.get("code_list") or []:
                out.append({"name": s.get("name", "?"), "continue_num": height})
        return out

    lines: list[str] = []
    snap_date = snapshot.get("date") or "—"
    display_date = (
        f"{snap_date[:4]}-{snap_date[4:6]}-{snap_date[6:]}"
        if snap_date and snap_date != "—"
        else snap_date
    )

    lines.append(f"# 同花顺涨停分析 — {display_date}")
    lines.append("")

    # ── 1. 近5日情绪趋势 ───────────────────────────────────
    lines.append("## 近5日情绪趋势")
    lines.append("")
    lines.append("| 日期 | 连板家数 | 当日最强板块（涨停数） |")
    lines.append("|------|---------|----------------------|")
    for day in history:
        d = day.get("date", "")
        d_str = f"{d[4:6]}/{d[6:]}" if len(d) == 8 else d
        lu_count = len(day.get("continuous_limit_up") or [])
        top3 = day.get("block_top", [])[:3]
        blk_str = (
            "、".join(f"{b['name']}({b.get('limit_up_num', '?')})" for b in top3)
            if top3
            else "—"
        )
        lines.append(f"| {d_str} | {lu_count} | {blk_str} |")
    lines.append("")

    # ── 2. 当日连板天梯 ───────────────────────────────────
    # snapshot 的 continuous_limit_up 是按板数分组的 {height, code_list} 结构
    raw_lu = snapshot.get("continuous_limit_up") or []
    if raw_lu and isinstance(raw_lu[0], dict) and "height" in raw_lu[0]:
        lu_list = sorted(
            _flatten_snap_lu(raw_lu), key=lambda x: -(x.get("continue_num") or 0)
        )
    else:
        lu_list = sorted(raw_lu, key=lambda x: -(x.get("continue_num") or 0))
    lines.append(f"## 连板天梯（{display_date}）")
    lines.append("")
    if lu_list:
        lines.append("| 板数 | 股票 |")
        lines.append("|-----|------|")
        for s in lu_list:
            num = s.get("continue_num") or 1
            name = s.get("name", "?")
            lines.append(f"| {num}板 | {name} |")
    else:
        lines.append("_当日无连板数据_")
    lines.append("")

    # ── 3. 当日最强板块 ──────────────────────────────────
    bt_list = snapshot.get("block_top") or []
    lines.append(f"## 最强板块 Top10（{display_date}）")
    lines.append("")
    if bt_list:
        lines.append("| 排名 | 板块 | 涨停数 | 板块涨幅 | 代表股（前3） |")
        lines.append("|-----|------|-------|---------|-------------|")
        for i, blk in enumerate(bt_list[:10], 1):
            blk_name = blk.get("name", "?")
            lu_num = blk.get("limit_up_num", "?")
            chg = blk.get("change")
            chg_str = (
                f"+{chg:.2f}%"
                if chg and chg > 0
                else (f"{chg:.2f}%" if chg is not None else "—")
            )
            stocks = blk.get("stock_list") or []
            rep = "、".join(s.get("name", "") for s in stocks[:3]) or "—"
            lines.append(f"| {i} | {blk_name} | {lu_num} | {chg_str} | {rep} |")
    else:
        lines.append("_当日无板块数据_")
    lines.append("")

    # ── 4. 热门板块详情（前5板块，每板块列出涨停股） ─────────
    lines.append(f"## 热门板块个股明细（前5板块）")
    lines.append("")
    for blk in bt_list[:5]:
        blk_name = blk.get("name", "?")
        lu_num = blk.get("limit_up_num", "?")
        chg = blk.get("change")
        chg_str = (
            f"+{chg:.2f}%"
            if chg and chg > 0
            else (f"{chg:.2f}%" if chg is not None else "—")
        )
        lines.append(f"### {blk_name}（涨停{lu_num}家，板块{chg_str}）")
        lines.append("")
        stocks = blk.get("stock_list") or []
        if stocks:
            lines.append("| 股票 | 板数 | 涨幅 | 类型 |")
            lines.append("|------|-----|------|------|")
            for s in stocks:
                sname = s.get("name", "?")
                num = s.get("continue_num") or 1
                schg = s.get("change_rate")
                schg_str = (
                    f"+{schg:.1f}%"
                    if schg and schg > 0
                    else (f"{schg:.1f}%" if schg else "—")
                )
                raw_tag = s.get("change_tag") or s.get("reason_type")
                tag = _tag(raw_tag)
                lines.append(f"| {sname} | {num}板 | {schg_str} | {tag} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JRJ K线
# ---------------------------------------------------------------------------


def fetch_jrj_daily_kline(
    code: str, range_num: int = 80, timeout: float = 15.0
) -> list[dict[str, Any]]:
    cache_key = f"{code}_daily_{_now_ymd()}_{range_num}"
    cached = cache_get("kline", cache_key)
    if isinstance(cached, list):
        return cached
    secid = _to_jrj_security_id(code)
    url = "https://gateway.jrj.com/quot-kline?" + urlencode(
        {
            "format": "json",
            "securityId": secid,
            "type": "day",
            "direction": "left",
            "range.num": str(range_num),
            "range.begin": _now_ymd(),
        }
    )
    data = http_json(url, timeout=timeout)

    if isinstance(data, dict) and isinstance(data.get("value"), str):
        try:
            data = json.loads(data["value"])
        except json.JSONDecodeError:
            pass

    kline = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), dict):
            kline = data["data"].get("kline", []) or []
        elif isinstance(data.get("kline"), list):
            kline = data["kline"]

    out: list[dict[str, Any]] = []
    for item in kline:
        t = item.get("time") or item.get("nTime")
        if t is None:
            continue
        op = norm_price(item.get("open") if "open" in item else item.get("nOpenPx"))
        cp = norm_price(item.get("close") if "close" in item else item.get("nLastPx"))
        hp = norm_price(item.get("high") if "high" in item else item.get("nHighPx"))
        lp = norm_price(item.get("low") if "low" in item else item.get("nLowPx"))
        # 成交量: llVolume 是股数，转为手(100股)
        vol = item.get("volume") or item.get("llVolume", 0)
        if vol:
            try:
                vol = float(vol) / 100.0
            except (TypeError, ValueError):
                vol = 0.0
        else:
            vol = 0.0
        raw_amount = item.get("llValue") or item.get("amount") or item.get("nAmount") or 0
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            amount = 0.0

        raw_change_pct = (
            item.get("change_pct")
            or item.get("changePct")
            or item.get("chgPct")
            or item.get("nChgPct")
            or item.get("changeRatio")
        )
        try:
            change_pct = float(raw_change_pct) if raw_change_pct is not None else None
        except (TypeError, ValueError):
            change_pct = None

        out.append(
            {
                "time": int(t),
                "open": op,
                "close": cp,
                "high": hp,
                "low": lp,
                "volume": vol,
                "amount": amount,
                "change_pct": change_pct,
            }
        )
    out.sort(key=lambda x: x["time"])
    for idx in range(1, len(out)):
        if out[idx].get("change_pct") is not None:
            continue
        prev_close = out[idx - 1].get("close")
        curr_close = out[idx].get("close")
        if prev_close is None or curr_close is None or float(prev_close) <= 0:
            continue
        out[idx]["change_pct"] = round((float(curr_close) / float(prev_close) - 1.0) * 100.0, 2)
    cache_set("kline", cache_key, out, ttl_seconds=None)
    return out


def fetch_jrj_minute_kline(
    code: str,
    date: str | None = None,
    range_num: int = 241,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """获取个股1分钟K线数据。

    通过金融界 quot-kline 接口获取分钟级别 OHLCV 数据，免费无需认证。
    每个交易日约 241 条（含集合竞价和尾盘集合竞价）。

    Args:
        code: 6位股票代码，如 "000001"。
        date: 目标日期 YYYYMMDD，默认今天。
        range_num: 获取条数，默认 241（一个交易日）。
        timeout: HTTP 超时秒数。

    Returns:
        分钟K线列表，按时间升序，每条包含：
        - time:   Unix 时间戳（秒）
        - open:   开盘价
        - close:  收盘价
        - high:   最高价
        - low:    最低价
        - volume: 成交量
        - amount: 成交额
        - avg:    均价（接口提供）
        出错时返回空列表。
    """
    if date is None:
        date = _now_ymd()
    cache_key = f"{code}_minute_{date}_{range_num}"
    cached = cache_get("kline", cache_key)
    if isinstance(cached, list):
        return cached

    secid = _to_jrj_security_id(code)
    url = "https://gateway.jrj.com/quot-kline?" + urlencode(
        {
            "format": "json",
            "securityId": secid,
            "type": "1minkline",
            "direction": "left",
            "range.num": str(range_num),
            "range.begin": date,
        }
    )

    try:
        data = http_json(url, timeout=timeout)
    except Exception:
        return []

    if isinstance(data, dict) and isinstance(data.get("value"), str):
        try:
            data = json.loads(data["value"])
        except json.JSONDecodeError:
            pass

    kline: list[dict] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), dict):
            kline = data["data"].get("kline", []) or []
        elif isinstance(data.get("kline"), list):
            kline = data["kline"]

    out: list[dict[str, Any]] = []
    for item in kline:
        t = item.get("nTime") or item.get("time")
        if t is None:
            continue
        op = _norm_price(item.get("nOpenPx") if "nOpenPx" in item else item.get("open"))
        cp = _norm_price(
            item.get("nLastPx") if "nLastPx" in item else item.get("close")
        )
        hp = _norm_price(item.get("nHighPx") if "nHighPx" in item else item.get("high"))
        lp = _norm_price(item.get("nLowPx") if "nLowPx" in item else item.get("low"))
        vol = item.get("llVolume") or item.get("volume") or 0
        amt = item.get("llValue") or item.get("amount") or 0
        avg = _norm_price(item.get("nAvgPx") or 0)
        out.append(
            {
                "time": int(t),
                "open": op,
                "close": cp,
                "high": hp,
                "low": lp,
                "volume": int(vol),
                "amount": float(amt),
                "avg": avg,
            }
        )
    out.sort(key=lambda x: x["time"])
    # 盘中高时效，按设计 5 分钟；盘后也先保守缓存 5 分钟（后续可根据交易时段优化）
    cache_set("kline", cache_key, out, ttl_seconds=300)
    return out


# ---------------------------------------------------------------------------
# 情绪因子 & 交易信号
# ---------------------------------------------------------------------------


def _emotion_from_slopes(
    s3: float, s5: float, s10: float, s30: float
) -> tuple[int, str, str, float, str]:
    eps = 1e-6
    base = max(abs(s30), eps)

    if s3 <= 0 or s5 <= 0 or s10 <= 0:
        return (
            1,
            "\u60c5\u7eea\u4e0d\u4f73",
            "\u26aa",
            1.0,
            "\u77ed\u7ebf\u659c\u7387\u5b58\u5728\u975e\u6b63\u503c(3/5/10\u65e5\u4e2d\u81f3\u5c11\u4e00\u4e2a<=0)",
        )

    a1 = (s3 - s5) / base
    a2 = (s5 - s10) / base
    a3 = (s10 - s30) / base
    short_strength = ((s3 + s5) / 2.0) / max(s30, eps)
    acc_score = max(
        0.0,
        min(
            10.0,
            5.0
            + 1.8 * (0.4 * a1 + 0.35 * a2 + 0.25 * a3)
            + 0.8 * (short_strength - 1.0),
        ),
    )

    tol_chain = 0.98
    chain_soft = (s3 >= tol_chain * s5) and (s5 >= tol_chain * s10)
    strong_short = (s3 >= 2.0 * s30) and (s5 >= 1.5 * s30)

    if chain_soft and (s10 >= 1.1 * s30) and (acc_score >= 8.2):
        return (
            5,
            "\u4e3b\u5347\u5f3a\u5316",
            "\U0001f534",
            10.0,
            f"\u52a0\u901f\u7ed3\u6784\u5f3a(3/5/10/30={s3:.3f}/{s5:.3f}/{s10:.3f}/{s30:.3f}), acc={acc_score:.2f}",
        )

    if strong_short and (s10 >= 0.85 * s30) and (acc_score >= 7.2):
        return (
            4,
            "\u60c5\u7eea\u504f\u5f3a",
            "\U0001f7e0",
            8.5,
            f"\u4e3b\u5347\u7279\u4f8b, acc={acc_score:.2f}",
        )

    if chain_soft and (s10 >= 0.90 * s30) and (acc_score >= 6.0):
        return (
            4,
            "\u60c5\u7eea\u504f\u5f3a",
            "\U0001f7e0",
            8.0,
            f"\u77ed\u7ebf\u659c\u7387\u52a0\u901f(\u542b\u5bb9\u5dee), acc={acc_score:.2f}",
        )

    if chain_soft and (s10 >= 0.8 * s30) and (acc_score >= 4.8):
        return (
            3,
            "\u7a33\u5065\u4e0a\u884c",
            "\U0001f7e2",
            6.0,
            f"\u77ed\u7ebf\u4e0a\u884c10\u65e5\u63a5\u8fd130\u65e5(>=80%), acc={acc_score:.2f}",
        )

    if s3 > s30 and s5 > s30:
        return (
            2,
            "\u4e2d\u6027\u504f\u5f31",
            "\U0001f535",
            3.5,
            f"\u77ed\u7ebf\u5f3a\u4f46\u7ed3\u6784\u5206\u6b67, acc={acc_score:.2f}",
        )

    return (
        1,
        "\u60c5\u7eea\u4e0d\u4f73",
        "\u26aa",
        1.0,
        f"\u77ed\u7ebf\u672a\u660e\u663e\u5f3a\u4e8e\u957f\u671f, acc={acc_score:.2f}",
    )


def _trade_signal_from_ma(
    last_close: float, ma5: float, ma10: float, ma20: float
) -> tuple[str, str]:
    """趋势信号（仅供研究，不作为操作依据）。

    交易操作信号由 watchlist_monitor 提供。
    """
    return "观察", "趋势扫描仅供研究，交易信号见 watchlist_monitor"


# ---------------------------------------------------------------------------
# 均线跌破统计（内部辅助）
# ---------------------------------------------------------------------------


def _ma_below_stats(values: list[float], window: int) -> tuple[int, int, int, int]:
    if len(values) < window:
        return 0, 0, 0, 0
    flags: list[bool] = []
    valid = 0
    for i in range(len(values)):
        if i + 1 < window:
            flags.append(False)
            continue
        valid += 1
        ma = sum(values[i + 1 - window : i + 1]) / window
        flags.append(values[i] < ma)
    count = sum(flags)
    cur = 0
    for x in reversed(flags):
        if x:
            cur += 1
        else:
            break
    max_streak = run = 0
    for x in flags:
        if x:
            run += 1
            max_streak = max(max_streak, run)
        else:
            run = 0
    return count, cur, max_streak, valid


def _latest_rising(values: list[float], days: int) -> tuple[bool, int]:
    if not values:
        return False, 0
    streak = 1
    for i in range(len(values) - 1, 0, -1):
        if values[i] > values[i - 1]:
            streak += 1
        else:
            break
    if len(values) < days:
        return False, streak
    seg = values[-days:]
    ok = all(seg[i] > seg[i - 1] for i in range(1, len(seg)))
    return ok, streak


# ---------------------------------------------------------------------------
# 单股趋势分析
# ---------------------------------------------------------------------------


def analyze_trend(
    *,
    code: str,
    sc: str,
    name: str,
    rank: int,
    source: str,
    rule_bars: int = 30,
    sort_bars: int = 60,
    timeout: float = 15.0,
) -> tuple[TrendResult, list[dict[str, Any]]]:
    need_bars = max(rule_bars, sort_bars)
    kline = fetch_jrj_daily_kline(
        code, range_num=max(140, need_bars + 40), timeout=timeout
    )
    bars_30 = kline[-rule_bars:] if len(kline) >= rule_bars else []
    bars_60 = kline[-sort_bars:] if len(kline) >= sort_bars else []

    if len(bars_30) < rule_bars:
        tr = TrendResult.empty(
            code=code,
            name=name,
            sc=sc,
            rank=rank,
            source=source,
            reason=f"insufficient_rule_bars:{len(bars_30)}",
        )
        tr.emotion_reason = (
            "\u6837\u672c\u4e0d\u8db3\uff0c\u9ed8\u8ba4\u4f4e\u60c5\u7eea"
        )
        tr.trade_signal_reason = (
            "\u6837\u672c\u4e0d\u8db3\uff0c\u9ed8\u8ba4\u89c2\u5bdf"
        )
        return tr, bars_60 or bars_30

    closes_30 = [x["close"] for x in bars_30]

    # 红柱: close[t] > close[t-1] 且 close[t] >= open[t]
    start_idx = len(kline) - len(bars_30)
    red_days = 0
    for i in range(len(bars_30)):
        gidx = start_idx + i
        if gidx <= 0:
            continue
        if (
            kline[gidx]["close"] > kline[gidx - 1]["close"]
            and kline[gidx]["close"] >= kline[gidx]["open"]
        ):
            red_days += 1
    red_ratio = red_days / rule_bars
    holding = (
        "\u826f\u597d"
        if red_ratio >= 0.80
        else ("\u4e00\u822c" if red_ratio > 0.50 else "\u8f83\u5dee")
    )

    gain_30 = (
        (closes_30[-1] - closes_30[0]) / closes_30[0] * 100.0
        if closes_30[0] > 0
        else 0.0
    )
    up_days = sum(1 for i in range(1, rule_bars) if closes_30[i] > closes_30[i - 1])
    up_day_ratio = up_days / (rule_bars - 1)

    s3 = _window_slope_pct_per_day(closes_30, 3)
    s5 = _window_slope_pct_per_day(closes_30, 5)
    s10 = _window_slope_pct_per_day(closes_30, 10)
    slope_30 = _linear_slope(closes_30)
    s30 = (slope_30 / closes_30[0] * 100.0) if closes_30[0] > 0 else 0.0
    emotion_level, emotion_label, emotion_color, emotion_score, emotion_reason = (
        _emotion_from_slopes(s3, s5, s10, s30)
    )

    closes_60 = [x["close"] for x in bars_60]
    gain_60 = 0.0
    if len(bars_60) >= sort_bars and bars_60[0]["close"] > 0:
        gain_60 = (
            (bars_60[-1]["close"] - bars_60[0]["close"]) / bars_60[0]["close"] * 100.0
        )

    # 攻防统计
    change_pcts: list[float] = []
    for i in range(1, len(closes_60)):
        if closes_60[i - 1] > 0:
            change_pcts.append(
                (closes_60[i] - closes_60[i - 1]) / closes_60[i - 1] * 100.0
            )
    cd = len(change_pcts)
    attack8 = sum(1 for p in change_pcts if p >= 8.0)
    defense5 = sum(1 for p in change_pcts if p <= -5.0)

    # 均线跌破
    ma5_c, ma5_cur, ma5_max, ma5_v = _ma_below_stats(closes_60, 5)
    ma10_c, ma10_cur, ma10_max, ma10_v = _ma_below_stats(closes_60, 10)
    ma20_c, ma20_cur, ma20_max, ma20_v = _ma_below_stats(closes_60, 20)

    ma5_last = sum(closes_60[-5:]) / 5.0 if len(closes_60) >= 5 else 0.0
    ma10_last = sum(closes_60[-10:]) / 10.0 if len(closes_60) >= 10 else 0.0
    ma20_last = sum(closes_60[-20:]) / 20.0 if len(closes_60) >= 20 else 0.0
    last_close = closes_60[-1] if closes_60 else 0.0
    trade_signal, trade_signal_reason = _trade_signal_from_ma(
        last_close, ma5_last, ma10_last, ma20_last
    )

    # MA10 > MA20 天数（近20日）
    ma10_above_ma20_days = ma10_above_ma20_valid = 0
    if len(closes_60) >= 20:
        start = len(closes_60) - 20
        for i in range(start, len(closes_60)):
            if i + 1 < 20:
                continue
            m10 = sum(closes_60[i + 1 - 10 : i + 1]) / 10.0
            m20 = sum(closes_60[i + 1 - 20 : i + 1]) / 20.0
            ma10_above_ma20_valid += 1
            if m10 > m20:
                ma10_above_ma20_days += 1
    ma10_above_ma20_ratio = (
        ma10_above_ma20_days / ma10_above_ma20_valid
        if ma10_above_ma20_valid > 0
        else 0.0
    )

    # MA 序列
    ma10_series = [
        sum(closes_60[i + 1 - 10 : i + 1]) / 10.0
        for i in range(len(closes_60))
        if i + 1 >= 10
    ]
    ma20_series = [
        sum(closes_60[i + 1 - 20 : i + 1]) / 20.0
        for i in range(len(closes_60))
        if i + 1 >= 20
    ]

    ma10_rising_10d, ma10_rs = _latest_rising(ma10_series, 10)
    ma20_rising_streak = 1
    if ma20_series:
        for i in range(len(ma20_series) - 1, 0, -1):
            if ma20_series[i] > ma20_series[i - 1]:
                ma20_rising_streak += 1
            else:
                break
    ma20_up_days_20 = 0
    if len(ma20_series) >= 20:
        seg20 = ma20_series[-20:]
        ma20_up_days_20 = sum(
            1 for i in range(1, len(seg20)) if seg20[i] > seg20[i - 1]
        )
    ma20_rising_20d = ma20_up_days_20 >= 15

    ma_penalty = (
        ma5_c * 1.0
        + ma10_c * 1.2
        + ma20_c * 1.5
        + ma5_cur * 3.0
        + ma10_cur * 4.0
        + ma20_cur * 5.0
    )

    # 顶部形态排除
    top_10_below_30h = False
    if len(closes_30) >= 10:
        max_c30 = max(closes_30)
        top_10_below_30h = all(c < max_c30 for c in closes_30[-10:])
    death_cross = ma5_last > 0 and ma20_last > 0 and ma5_last < ma20_last
    top_excluded = top_10_below_30h and death_cross

    # 趋势判定
    reasons: list[str] = []
    if top_excluded:
        reasons.append("excluded_top_pattern")
    if ma10_above_ma20_ratio <= 0.60:
        reasons.append(f"ma10_gt_ma20_ratio20={ma10_above_ma20_ratio:.2f}<=0.60")
    if not ma20_rising_20d:
        reasons.append(f"ma20_up_days_20={ma20_up_days_20}<15")
    if not ma10_rising_10d:
        reasons.append(f"ma10_not_rising_10d(streak={ma10_rs})")
    pass_rule = len(reasons) == 0

    tr = TrendResult(
        code=code,
        name=name,
        sc=sc,
        rank=rank,
        source=source,
        bars_30=rule_bars,
        bars_60=len(bars_60),
        red_days=red_days,
        red_ratio=red_ratio,
        holding_experience=holding,
        gain_30_pct=gain_30,
        gain_60_pct=gain_60,
        up_day_ratio=up_day_ratio,
        slope_3_pct_per_day=s3,
        slope_5_pct_per_day=s5,
        slope_10_pct_per_day=s10,
        slope_30=slope_30,
        slope_30_pct_per_day=s30,
        ma5_below_count=ma5_c,
        ma5_current_below_streak=ma5_cur,
        ma5_max_below_streak=ma5_max,
        ma5_above_count=max(0, ma5_v - ma5_c),
        ma10_below_count=ma10_c,
        ma10_current_below_streak=ma10_cur,
        ma10_max_below_streak=ma10_max,
        ma10_above_count=max(0, ma10_v - ma10_c),
        ma10_above_ma20_days_20=ma10_above_ma20_days,
        ma10_above_ma20_ratio_20=ma10_above_ma20_ratio,
        ma10_rising_10d=ma10_rising_10d,
        ma10_rising_streak=ma10_rs,
        ma20_below_count=ma20_c,
        ma20_current_below_streak=ma20_cur,
        ma20_max_below_streak=ma20_max,
        ma20_above_count=max(0, ma20_v - ma20_c),
        ma20_rising_20d=ma20_rising_20d,
        ma20_up_days_20=ma20_up_days_20,
        ma20_rising_streak=ma20_rising_streak,
        attack_gain8_days=attack8,
        attack_gain8_ratio=attack8 / cd if cd > 0 else 0.0,
        defense_drop5_days=defense5,
        defense_safe_ratio=(cd - defense5) / cd if cd > 0 else 0.0,
        ma_support_penalty=ma_penalty,
        score_emotion_10=emotion_score,
        emotion_level=emotion_level,
        emotion_label=emotion_label,
        emotion_color=emotion_color,
        emotion_reason=emotion_reason,
        trade_signal=trade_signal,
        trade_signal_reason=trade_signal_reason,
        ma5_dist_pct=(last_close - ma5_last) / ma5_last * 100 if ma5_last > 0 else 0.0,
        ma10_dist_pct=(last_close - ma10_last) / ma10_last * 100 if ma10_last > 0 else 0.0,
        is_uptrend=pass_rule,
        reason="pass" if pass_rule else ";".join(reasons),
    )
    return tr, bars_60 or bars_30


# ---------------------------------------------------------------------------
# 评分
# ---------------------------------------------------------------------------


def apply_scoring(results: list[TrendResult]) -> None:
    if not results:
        return
    g30 = [r.gain_30_pct for r in results]
    g60 = [r.gain_60_pct for r in results]
    a5 = [r.ma5_above_count for r in results]
    a10 = [r.ma10_above_count for r in results]
    a20 = [r.ma20_above_count for r in results]
    b5 = [r.ma5_below_count for r in results]
    b10 = [r.ma10_below_count for r in results]
    b20 = [r.ma20_below_count for r in results]
    m5 = [r.ma5_max_below_streak for r in results]
    m10 = [r.ma10_max_below_streak for r in results]
    m20 = [r.ma20_max_below_streak for r in results]
    ar = [r.attack_gain8_ratio for r in results]
    dd = [r.defense_drop5_days for r in results]

    for r in results:
        s30 = (
            _decile_score(g30, r.gain_30_pct) * 0.4
            + _decile_score(g60, r.gain_60_pct) * 0.6
        )
        sup = (
            _decile_score(a5, r.ma5_above_count) * 0.2
            + _decile_score(a10, r.ma10_above_count) * 0.3
            + _decile_score(a20, r.ma20_above_count) * 0.5
        )
        risk = (
            _decile_score(b5, r.ma5_below_count, False) * 0.15
            + _decile_score(b10, r.ma10_below_count, False) * 0.2
            + _decile_score(b20, r.ma20_below_count, False) * 0.25
            + _decile_score(m5, r.ma5_max_below_streak, False) * 0.1
            + _decile_score(m10, r.ma10_max_below_streak, False) * 0.12
            + _decile_score(m20, r.ma20_max_below_streak, False) * 0.18
        )
        rob = (
            _decile_score(ar, r.attack_gain8_ratio) * 0.55
            + _decile_score(dd, r.defense_drop5_days, False) * 0.45
        )
        emo = r.score_emotion_10
        t10 = s30 * 0.30 + sup * 0.25 + risk * 0.15 + rob * 0.20 + emo * 0.10
        t100 = max(0.0, min(100.0, (t10 - 1.0) / 9.0 * 100.0))
        r.score_trend_10 = round(s30, 2)
        r.score_support_10 = round(sup, 2)
        r.score_risk_10 = round(risk, 2)
        r.score_robust_10 = round(rob, 2)
        r.score_emotion_10 = round(emo, 2)
        r.score_total_100 = round(t100, 1)
        r.star_rating = _to_star(t100)


# ---------------------------------------------------------------------------
# 批量扫描
# ---------------------------------------------------------------------------


def scan_all(
    candidates: list[dict[str, Any]],
    *,
    rule_bars: int = 30,
    sort_bars: int = 60,
    workers: int = 10,
    timeout: float = 15.0,
) -> list[TrendResult]:
    """并发扫描所有候选股，返回含评分的 TrendResult 列表（按排名序）。"""
    results: list[TrendResult] = []

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {}
        for x in candidates:
            fut = ex.submit(
                analyze_trend,
                code=x["code"],
                sc=x["sc"],
                name=x.get("name", "\u672a\u77e5"),
                rank=x["rank"],
                source=x["from"],
                rule_bars=rule_bars,
                sort_bars=sort_bars,
                timeout=timeout,
            )
            futs[fut] = x
        for fut in as_completed(futs):
            x = futs[fut]
            try:
                tr, _ = fut.result()
                results.append(tr)
            except Exception as err:
                tr = TrendResult.empty(
                    code=x["code"],
                    name=x.get("name", "\u672a\u77e5"),
                    sc=x["sc"],
                    rank=x["rank"],
                    source=x["from"],
                    reason=f"error:{type(err).__name__}",
                )
                tr.emotion_reason = f"\u8ba1\u7b97\u5931\u8d25:{type(err).__name__}"
                tr.trade_signal_reason = (
                    f"\u8ba1\u7b97\u5931\u8d25:{type(err).__name__}"
                )
                results.append(tr)

    apply_scoring(results)

    # 按排名排序
    results.sort(key=lambda r: (r.rank if r.rank > 0 else math.inf, r.sc))
    return results


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------


def format_report_md(
    results: list[TrendResult], *, eastmoney_count: int = 0, ths_date: str | None = None
) -> str:
    passed = [x for x in results if x.is_uptrend and x.star_rating >= 4]
    passed.sort(
        key=lambda r: (
            -r.star_rating,
            -r.score_total_100,
            -r.emotion_level,
            r.ma_support_penalty,
            -(r.gain_60_pct),
        )
    )
    failed = sum(1 for x in results if x.reason.startswith(("error", "insufficient")))

    lines = [
        "# A\u80a1\u8d8b\u52bf\u626b\u63cf\u7ed3\u679c",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u4e1c\u65b9\u8d22\u5bcc\u5019\u9009\u6570: {eastmoney_count}",
        f"- \u540c\u82b1\u987a\u5feb\u7167\u65e5\u671f: {ths_date or 'N/A'}",
        f"- \u5df2\u5206\u6790\u80a1\u7968\u6570: {len(results)}",
        f"- \u6ee1\u8db3\u4e0a\u6da8\u8d8b\u52bf\u6570: {len(passed)}",
        f"- \u5206\u6790\u5931\u8d25/\u6570\u636e\u4e0d\u8db3: {failed}",
        "- \u786c\u95e8\u69db: MA10>MA20\u5360\u6bd4>60%, MA20\u62ac\u5347>=15/20\u65e5, MA10\u8fde\u7eed10\u65e5\u62ac\u9ad8",
        "- \u5254\u9664: \u8fd110\u65e5\u6536\u76d8\u5747\u4f4e\u4e8e30\u65e5\u6700\u9ad8\u4e14MA5<MA20",
        "",
        "## \u7b26\u5408\u6761\u4ef6\u80a1\u7968",
        "",
    ]
    if not passed:
        lines.append(
            "\u672a\u7b5b\u9009\u5230\u7b26\u5408\u6761\u4ef6\u7684\u80a1\u7968\u3002"
        )
    else:
        lines.append(
            "| \u6392\u540d | \u80a1\u7968 | \u4ee3\u7801 | \u661f\u7ea7 | \u60c5\u7eea | \u6301\u80a1\u4f53\u9a8c | \u603b\u5206 | \u4ea4\u6613\u5efa\u8bae |"
        )
        lines.append("|---:|---|---|---|---|---|---:|---|")
        for x in passed:
            lines.append(
                f"| {x.rank} | {x.name} | {x.sc} | {_format_star_emoji(x.star_rating)} "
                f"| {x.emotion_color}L{x.emotion_level} | {x.holding_experience} "
                f"| {x.score_total_100:.1f} | {x.trade_signal} |"
            )
    return "\n".join(lines)
