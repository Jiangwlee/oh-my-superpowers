"""日内行情分析工具。

为复盘 AI 提供四个按需调用的分析函数，供 LLM 在交易复盘时自主调用：

- get_intraday_summary:    全天行情摘要（30分钟聚合）
- get_trade_context:       操作时刻前后现场还原
- get_opening_context:     开盘背景（跳空/MA位置/前日趋势）
- get_relative_strength:   个股 vs 大盘全天相对强弱

数据源：金融界 quot-kline 接口（免费，无需认证）
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from ashare_data.core.utils import safe_float
from ashare_data.fetchers.trend_scanner import fetch_jrj_daily_kline, fetch_jrj_minute_kline

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))

# 30分钟周期标签（按交易时间顺序）
_PERIOD_ORDER = [
    "09:30-10:00",
    "10:00-10:30",
    "10:30-11:00",
    "11:00-11:30",
    "13:00-13:30",
    "13:30-14:00",
    "14:00-14:30",
    "14:30-15:00",
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _normalize_date(date: str | None) -> str:
    """统一日期格式为 YYYYMMDD。"""
    if date is None:
        return datetime.now(tz=_CN_TZ).strftime("%Y%m%d")
    date = date.strip()
    if len(date) == 8 and date.isdigit():
        return date
    if len(date) == 10 and date[4] == "-":
        return date.replace("-", "")
    return date


def _ts_to_hhmm(ts: int) -> str:
    """Unix 时间戳 → HH:MM（北京时间）。"""
    if ts <= 0:
        return ""
    try:
        dt = datetime.fromtimestamp(ts, tz=_CN_TZ)
        return dt.strftime("%H:%M")
    except Exception:
        return ""


def _bar_hm(ts: int) -> tuple[int, int]:
    """Unix 时间戳 → (hour, minute) 北京时间。"""
    if ts <= 0:
        return 0, 0
    dt = datetime.fromtimestamp(ts, tz=_CN_TZ)
    return dt.hour, dt.minute


def _minute_to_period(hour: int, minute: int) -> str | None:
    """将分钟时间映射到 30 分钟周期标签，午间休市返回 None。"""
    m = hour * 60 + minute
    if 9 * 60 + 30 <= m < 10 * 60:
        return "09:30-10:00"
    if 10 * 60 <= m < 10 * 60 + 30:
        return "10:00-10:30"
    if 10 * 60 + 30 <= m < 11 * 60:
        return "10:30-11:00"
    if 11 * 60 <= m <= 11 * 60 + 30:
        return "11:00-11:30"
    if 13 * 60 <= m < 13 * 60 + 30:
        return "13:00-13:30"
    if 13 * 60 + 30 <= m < 14 * 60:
        return "13:30-14:00"
    if 14 * 60 <= m < 14 * 60 + 30:
        return "14:00-14:30"
    if 14 * 60 + 30 <= m <= 15 * 60:
        return "14:30-15:00"
    return None


def _pct(a: float, b: float) -> float:
    """(a - b) / b * 100，b=0 时返回 0。"""
    return (a - b) / b * 100.0 if b > 0 else 0.0


# ---------------------------------------------------------------------------
# 工具一：全天日内行情摘要
# ---------------------------------------------------------------------------


def get_intraday_summary(code: str, date: str | None = None) -> dict[str, Any]:
    """获取个股全天日内行情摘要（30分钟聚合）。

    Args:
        code: 6位股票代码，如 "000338"。
        date: 目标日期，YYYYMMDD 或 YYYY-MM-DD，默认今天。

    Returns:
        包含开盘跳空、日内振幅、30分钟聚合K线等字段的字典。
        数据不可用时返回含 error 字段的字典。
    """
    date_ymd = _normalize_date(date)

    minute_bars = fetch_jrj_minute_kline(code, date=date_ymd)
    if not minute_bars:
        return {"code": code, "date": date_ymd, "error": "no_minute_data"}

    daily_bars = fetch_jrj_daily_kline(code, range_num=5)
    today_int = int(date_ymd)
    prev_close = 0.0
    for bar in reversed(daily_bars):
        if safe_float(bar.get("time", 0)) < today_int:
            prev_close = safe_float(bar.get("close"))
            break

    # 全天基础统计
    valid_bars = [b for b in minute_bars if safe_float(b.get("close")) > 0]
    if not valid_bars:
        return {"code": code, "date": date_ymd, "error": "empty_bars"}

    opens = [safe_float(b.get("open")) for b in valid_bars if safe_float(b.get("open")) > 0]
    closes = [safe_float(b.get("close")) for b in valid_bars]
    highs = [safe_float(b.get("high")) for b in valid_bars if safe_float(b.get("high")) > 0]
    lows = [safe_float(b.get("low")) for b in valid_bars if safe_float(b.get("low")) > 0]
    volumes = [int(b.get("volume", 0)) for b in valid_bars]

    day_open = opens[0] if opens else 0.0
    day_close = closes[-1] if closes else 0.0
    day_high = max(highs) if highs else 0.0
    day_low = min(lows) if lows else 0.0
    vol_total = sum(volumes)

    high_bar = max(valid_bars, key=lambda b: safe_float(b.get("high")))
    low_bar = min(valid_bars, key=lambda b: safe_float(b.get("low"), float("inf")))

    # 30分钟聚合
    period_buckets: dict[str, list[dict[str, Any]]] = {}
    for bar in minute_bars:
        h, m = _bar_hm(int(bar.get("time", 0)))
        period = _minute_to_period(h, m)
        if period:
            period_buckets.setdefault(period, []).append(bar)

    bars_30min: list[dict[str, Any]] = []
    for period in _PERIOD_ORDER:
        bars = period_buckets.get(period, [])
        if not bars:
            continue
        p_open = safe_float(bars[0].get("open") or bars[0].get("close"))
        p_close = safe_float(bars[-1].get("close"))
        p_high = max(safe_float(b.get("high")) for b in bars)
        p_low = min((safe_float(b.get("low")) for b in bars if safe_float(b.get("low")) > 0), default=p_close)
        p_vol = sum(int(b.get("volume", 0)) for b in bars)
        bars_30min.append(
            {
                "period": period,
                "open": round(p_open, 3),
                "close": round(p_close, 3),
                "high": round(p_high, 3),
                "low": round(p_low, 3),
                "volume": p_vol,
                "change_pct": round(_pct(p_close, p_open), 2),
            }
        )

    return {
        "code": code,
        "date": date_ymd,
        "prev_close": round(prev_close, 3),
        "open": round(day_open, 3),
        "close": round(day_close, 3),
        "high": round(day_high, 3),
        "low": round(day_low, 3),
        "opening_gap_pct": round(_pct(day_open, prev_close), 2),
        "final_change_pct": round(_pct(day_close, prev_close), 2),
        "intraday_range_pct": round(_pct(day_high, day_low), 2),
        "high_time": _ts_to_hhmm(int(high_bar.get("time", 0))),
        "low_time": _ts_to_hhmm(int(low_bar.get("time", 0))),
        "volume_total": vol_total,
        "bars_30min": bars_30min,
    }


# ---------------------------------------------------------------------------
# 工具二：操作时刻前后现场还原
# ---------------------------------------------------------------------------


def get_trade_context(
    code: str,
    date: str | None = None,
    trade_time: str = "",
    trade_price: float = 0.0,
    window_minutes: int = 30,
) -> dict[str, Any]:
    """还原某笔操作时刻前后的行情现场。

    Args:
        code: 6位股票代码。
        date: 目标日期，YYYYMMDD 或 YYYY-MM-DD。
        trade_time: 操作时间 HHMMSS（来自 order_list.time 字段）。
        trade_price: 成交价格（来自 order_list.deal_price 字段）。
        window_minutes: 前后各取多少分钟，默认30分钟。

    Returns:
        含 before/after 行情变化、日内位置等字段的字典。
    """
    date_ymd = _normalize_date(date)
    minute_bars = fetch_jrj_minute_kline(code, date=date_ymd)
    if not minute_bars:
        return {"code": code, "date": date_ymd, "trade_time": trade_time, "error": "no_minute_data"}

    # 解析操作时间 → Unix 时间戳范围
    try:
        h = int(trade_time[:2])
        m_min = int(trade_time[2:4])
        target_minutes = h * 60 + m_min
    except (ValueError, IndexError):
        return {"code": code, "date": date_ymd, "trade_time": trade_time, "error": "invalid_trade_time"}

    before_start = target_minutes - window_minutes
    after_end = target_minutes + window_minutes

    context_bars: list[dict[str, Any]] = []
    trade_bar: dict[str, Any] | None = None
    min_dist = float("inf")

    for bar in minute_bars:
        bh, bm = _bar_hm(int(bar.get("time", 0)))
        bar_minutes = bh * 60 + bm
        if before_start <= bar_minutes <= after_end:
            context_bars.append(bar)
        dist = abs(bar_minutes - target_minutes)
        if dist < min_dist:
            min_dist = dist
            trade_bar = bar

    if not context_bars:
        return {"code": code, "date": date_ymd, "trade_time": trade_time, "error": "no_context_bars"}

    # 全天高低（用于日内位置计算）
    all_highs = [safe_float(b.get("high")) for b in minute_bars if safe_float(b.get("high")) > 0]
    all_lows = [safe_float(b.get("low")) for b in minute_bars if safe_float(b.get("low")) > 0]
    day_high = max(all_highs) if all_highs else 0.0
    day_low = min(all_lows) if all_lows else 0.0

    # 操作价格在全天区间的位置（0=最低，1=最高）
    if trade_price > 0 and day_high > day_low:
        day_pos_pct = round((trade_price - day_low) / (day_high - day_low) * 100, 1)
    elif trade_bar:
        p = safe_float(trade_bar.get("close"))
        day_pos_pct = round((p - day_low) / (day_high - day_low) * 100, 1) if day_high > day_low else 50.0
    else:
        day_pos_pct = 50.0

    # 操作前行情变化
    before_bars = [b for b in context_bars if _bar_hm(int(b.get("time", 0)))[0] * 60 + _bar_hm(int(b.get("time", 0)))[1] <= target_minutes]
    after_bars = [b for b in context_bars if _bar_hm(int(b.get("time", 0)))[0] * 60 + _bar_hm(int(b.get("time", 0)))[1] > target_minutes]

    before_summary: dict[str, Any] = {}
    if before_bars:
        b_open = safe_float(before_bars[0].get("open") or before_bars[0].get("close"))
        b_close = safe_float(before_bars[-1].get("close"))
        before_summary = {
            "bars": len(before_bars),
            "price_start": round(b_open, 3),
            "price_at_trade": round(trade_price or b_close, 3),
            "change_pct": round(_pct(b_close, b_open), 2),
            "trend": "上涨" if b_close > b_open else ("下跌" if b_close < b_open else "横盘"),
        }

    after_summary: dict[str, Any] = {}
    if after_bars:
        a_open = safe_float(after_bars[0].get("open") or after_bars[0].get("close"))
        a_close = safe_float(after_bars[-1].get("close"))
        ref = trade_price if trade_price > 0 else a_open
        after_summary = {
            "bars": len(after_bars),
            "price_end": round(a_close, 3),
            "change_from_trade_pct": round(_pct(a_close, ref), 2),
            "trend": "继续上涨" if a_close > ref else ("继续下跌" if a_close < ref else "横盘"),
        }

    # 简化 context_bars 供 LLM 阅读（每5分钟一条）
    simplified: list[dict[str, Any]] = []
    for i in range(0, len(context_bars), 5):
        group = context_bars[i : i + 5]
        if not group:
            continue
        g_open = safe_float(group[0].get("open") or group[0].get("close"))
        g_close = safe_float(group[-1].get("close"))
        g_high = max(safe_float(b.get("high")) for b in group)
        g_low = min((safe_float(b.get("low")) for b in group if safe_float(b.get("low")) > 0), default=g_close)
        simplified.append(
            {
                "time": _ts_to_hhmm(int(group[0].get("time", 0))),
                "close": round(g_close, 3),
                "high": round(g_high, 3),
                "low": round(g_low, 3),
                "change_pct": round(_pct(g_close, g_open), 2),
                "volume": sum(int(b.get("volume", 0)) for b in group),
            }
        )

    return {
        "code": code,
        "date": date_ymd,
        "trade_time": trade_time[:2] + ":" + trade_time[2:4] if len(trade_time) >= 4 else trade_time,
        "trade_price": trade_price,
        "day_high": round(day_high, 3),
        "day_low": round(day_low, 3),
        "day_position_pct": day_pos_pct,
        "before_30min": before_summary,
        "after_30min": after_summary,
        "context_5min_bars": simplified,
    }


# ---------------------------------------------------------------------------
# 工具三：开盘背景
# ---------------------------------------------------------------------------


def get_opening_context(code: str, date: str | None = None) -> dict[str, Any]:
    """获取个股的开盘背景信号（适合反事实分析：如果在开盘前看，你会如何判断？）。

    Args:
        code: 6位股票代码。
        date: 目标日期，YYYYMMDD 或 YYYY-MM-DD。

    Returns:
        含跳空幅度、前日趋势、MA位置、开盘30分钟表现的字典。
    """
    date_ymd = _normalize_date(date)

    daily_bars = fetch_jrj_daily_kline(code, range_num=25)
    today_int = int(date_ymd)

    # 分离历史 bar（不含今日）和今日 bar
    hist_bars = [b for b in daily_bars if int(safe_float(b.get("time", 0))) < today_int]
    today_bar = next((b for b in daily_bars if int(safe_float(b.get("time", 0))) == today_int), None)

    prev_close = safe_float(hist_bars[-1].get("close")) if hist_bars else 0.0
    today_open = safe_float(today_bar.get("open")) if today_bar else 0.0

    # MA 计算（基于昨日及之前的收盘价）
    hist_closes = [safe_float(b.get("close")) for b in hist_bars if safe_float(b.get("close")) > 0]
    ma5 = sum(hist_closes[-5:]) / 5.0 if len(hist_closes) >= 5 else 0.0
    ma10 = sum(hist_closes[-10:]) / 10.0 if len(hist_closes) >= 10 else 0.0
    ma20 = sum(hist_closes[-20:]) / 20.0 if len(hist_closes) >= 20 else 0.0

    # 前5日涨跌（判断短期趋势）
    recent_trend = "数据不足"
    if len(hist_closes) >= 5:
        change_5d = _pct(hist_closes[-1], hist_closes[-5])
        recent_trend = f"近5日 {change_5d:+.1f}%（{'上涨' if change_5d > 1 else '下跌' if change_5d < -1 else '横盘'}）"

    opening_gap_pct = _pct(today_open, prev_close)
    if opening_gap_pct > 1.0:
        gap_desc = f"高开 +{opening_gap_pct:.1f}%"
    elif opening_gap_pct < -1.0:
        gap_desc = f"低开 {opening_gap_pct:.1f}%"
    else:
        gap_desc = f"平开 {opening_gap_pct:+.1f}%"

    # 开盘30分钟表现（取自分钟K线）
    minute_bars = fetch_jrj_minute_kline(code, date=date_ymd)
    first_30min: dict[str, Any] = {}
    if minute_bars:
        open_bars = [
            b for b in minute_bars
            if (lambda h, m: 9 * 60 + 30 <= h * 60 + m < 10 * 60)(*_bar_hm(int(b.get("time", 0))))
        ]
        if open_bars:
            o_open = safe_float(open_bars[0].get("open") or open_bars[0].get("close"))
            o_close = safe_float(open_bars[-1].get("close"))
            o_high = max(safe_float(b.get("high")) for b in open_bars)
            o_low = min((safe_float(b.get("low")) for b in open_bars if safe_float(b.get("low")) > 0), default=o_close)
            o_vol = sum(int(b.get("volume", 0)) for b in open_bars)
            first_30min = {
                "open": round(o_open, 3),
                "close": round(o_close, 3),
                "high": round(o_high, 3),
                "low": round(o_low, 3),
                "volume": o_vol,
                "change_pct": round(_pct(o_close, o_open), 2),
                "direction": "上涨" if o_close > o_open * 1.003 else ("下跌" if o_close < o_open * 0.997 else "横盘"),
            }

    result: dict[str, Any] = {
        "code": code,
        "date": date_ymd,
        "prev_close": round(prev_close, 3),
        "open": round(today_open, 3),
        "opening_gap_pct": round(opening_gap_pct, 2),
        "gap_description": gap_desc,
        "recent_trend_5d": recent_trend,
    }
    if ma5 > 0:
        result["ma5"] = round(ma5, 3)
        result["price_vs_ma5_pct"] = round(_pct(today_open, ma5), 2)
    if ma10 > 0:
        result["ma10"] = round(ma10, 3)
        result["price_vs_ma10_pct"] = round(_pct(today_open, ma10), 2)
    if ma20 > 0:
        result["ma20"] = round(ma20, 3)
        result["price_vs_ma20_pct"] = round(_pct(today_open, ma20), 2)
    if ma5 > 0 and ma10 > 0:
        result["ma_alignment"] = "多头排列" if ma5 > ma10 > (ma20 if ma20 > 0 else ma10) else "空头排列" if ma5 < ma10 else "混合"
    if first_30min:
        result["first_30min"] = first_30min

    return result


# ---------------------------------------------------------------------------
# 工具四：个股 vs 大盘相对强弱
# ---------------------------------------------------------------------------


def get_relative_strength(
    code: str,
    date: str | None = None,
    benchmark: str = "000001",
) -> dict[str, Any]:
    """计算个股全天相对大盘的强弱对比。

    Args:
        code: 6位股票代码。
        date: 目标日期，YYYYMMDD 或 YYYY-MM-DD。
        benchmark: 基准指数代码，默认 000001（上证综指）。

    Returns:
        含4-5个时间节点相对强弱对比的字典。大盘数据不可用时仅返回个股曲线。
    """
    date_ymd = _normalize_date(date)

    stock_bars = fetch_jrj_minute_kline(code, date=date_ymd)
    bench_bars = fetch_jrj_minute_kline(benchmark, date=date_ymd)

    if not stock_bars:
        return {"code": code, "date": date_ymd, "benchmark": benchmark, "error": "no_stock_data"}

    def _build_normalized(bars: list[dict[str, Any]]) -> dict[int, float]:
        """将 1分钟K线按分钟索引归一化（以第一根bar的open为基准）。"""
        if not bars:
            return {}
        base = safe_float(bars[0].get("open") or bars[0].get("close"))
        if base <= 0:
            return {}
        result: dict[int, float] = {}
        for bar in bars:
            h, m = _bar_hm(int(bar.get("time", 0)))
            mins = h * 60 + m
            close = safe_float(bar.get("close"))
            if close > 0:
                result[mins] = _pct(close, base)
        return result

    stock_norm = _build_normalized(stock_bars)
    bench_norm = _build_normalized(bench_bars) if bench_bars else {}

    # 对比节点：10:00 / 11:00 / 13:30 / 14:30 / 15:00
    checkpoints = [
        (10 * 60, "10:00"),
        (11 * 60, "11:00"),
        (13 * 60 + 30, "13:30"),
        (14 * 60 + 30, "14:30"),
        (15 * 60, "15:00"),
    ]

    comparison: list[dict[str, Any]] = []
    for target_mins, label in checkpoints:
        # 找最接近目标分钟的实际数据
        def _nearest(norm: dict[int, float], target: int) -> float | None:
            if not norm:
                return None
            closest = min(norm.keys(), key=lambda k: abs(k - target))
            if abs(closest - target) <= 5:  # 最多允许5分钟偏差
                return norm[closest]
            return None

        s_ret = _nearest(stock_norm, target_mins)
        b_ret = _nearest(bench_norm, target_mins)

        if s_ret is None:
            continue

        point: dict[str, Any] = {
            "time": label,
            "stock_return_pct": round(s_ret, 2),
        }
        if b_ret is not None:
            point["bench_return_pct"] = round(b_ret, 2)
            diff = s_ret - b_ret
            point["relative_pct"] = round(diff, 2)
            point["assessment"] = (
                "明显强于大盘" if diff > 1.5
                else "略强于大盘" if diff > 0.3
                else "略弱于大盘" if diff < -0.3
                else "明显弱于大盘" if diff < -1.5
                else "与大盘同步"
            )
        comparison.append(point)

    result: dict[str, Any] = {
        "code": code,
        "date": date_ymd,
        "benchmark": benchmark,
        "comparison": comparison,
    }
    if not bench_bars:
        result["note"] = "大盘分钟K线数据不可用，仅显示个股曲线"
    return result
