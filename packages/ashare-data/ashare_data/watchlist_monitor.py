#!/usr/bin/env python3
"""Watchlist intraday signal scanner.

Purpose: Scan watchlist active stocks every 10 minutes during trading hours,
         identify buy-dip opportunities using MA position and volume signals.
Input:   ~/.ashare-assistant/memory/watchlist.json, Tencent/East-Money APIs
Output:  ~/.ashare-assistant/signals/watchlist_signals.json (overwrite)

Public API:
    main()  -- CLI entry point (ashare-wl-monitor)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from ashare_data.core.config import ASHARE_HOME
from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_bytes, http_text
from ashare_data.core.watchlist import load as load_watchlist
from ashare_data.core.utils import norm_price as _norm_price
from ashare_data.fetchers.trend_scanner import fetch_jrj_daily_kline
from ashare_data.fetchers.market_sentiment import MarketSentiment, fetch_market_sentiment

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))
_SIGNALS_DIR = ASHARE_HOME / "signals"
_SIGNALS_FILE = _SIGNALS_DIR / "watchlist_signals.json"
_CONFIG_FILE = ASHARE_HOME / "config.json"


# ---------------------------------------------------------------------------
# Trading hours
# ---------------------------------------------------------------------------


def _is_trading_time() -> bool:
    """检查当前北京时间是否在交易时段（9:30–15:00）。"""
    now = datetime.now(tz=_CN_TZ)
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 30) <= minutes <= 15 * 60


# ---------------------------------------------------------------------------
# App config
# ---------------------------------------------------------------------------


def _load_app_config() -> dict[str, Any]:
    """读取 ~/.ashare-assistant/config.json。文件不存在时返回空 dict。"""
    if not _CONFIG_FILE.exists():
        return {}
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.warning("读取 config.json 失败，使用空配置")
        return {}


# ---------------------------------------------------------------------------
# East Money daily kline with volume
# ---------------------------------------------------------------------------


@dataclass
class _KlineBar:
    date: str       # YYYY-MM-DD
    open: float
    close: float
    high: float
    low: float
    volume: float   # 手（1手=100股）


def _em_secid(code: str) -> str:
    """6位代码 → 东方财富 secid（1.=沪，0.=深/创）。"""
    return f"1.{code}" if code.startswith("6") else f"0.{code}"


def _to_jrj_security_id(code: str) -> str:
    """6位代码 → JRJ securityId（1=沪，2=深）。"""
    return f"1{code}" if code.startswith("6") else f"2{code}"


# 缓存 TTL
_WEEKLY_CACHE_TTL = 7 * 24 * 3600


def _parse_jrj_kline(kline: list[dict], is_weekly: bool = False) -> list[_KlineBar]:
    """解析 JRJ K线数据为 _KlineBar 列表。

    JRJ 日线和周线返回的数据结构相同，都使用 nTime/nOpenPx 等字段。

    Args:
        kline: JRJ API 返回的 K线列表。
        is_weekly: 是否为周K（字段名相同，无需区分）。

    Returns:
        _KlineBar 列表。
    """
    bars: list[_KlineBar] = []
    for item in kline:
        # JRJ 日线/周线都使用 nTime, nOpenPx, nLastPx, nHighPx, nLowPx, llVolume
        t = item.get("nTime")
        if not t:
            continue
        ts = str(int(t))
        if len(ts) != 8:
            continue

        open_px = _norm_price(item.get("nOpenPx"))
        close_px = _norm_price(item.get("nLastPx"))
        high_px = _norm_price(item.get("nHighPx"))
        low_px = _norm_price(item.get("nLowPx"))
        # llVolume 是股数，转为手(100股)
        vol_raw = item.get("llVolume", 0) or 0
        try:
            vol = float(vol_raw) / 100.0
        except (TypeError, ValueError):
            vol = 0.0

        date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        bars.append(
            _KlineBar(
                date=date_str,
                open=open_px,
                close=close_px,
                high=high_px,
                low=low_px,
                volume=vol,
            )
        )
    return bars


def _fetch_jrj_kline(code: str, ktype: str = "day", days: int = 150) -> list[_KlineBar]:
    """从金融界获取K线数据。

    Args:
        code: 6位股票代码。
        ktype: K线类型，"day" 或 "week"。
        days: 获取数量（天数或周数）。

    Returns:
        K线列表，按日期升序。
    """
    import requests

    secid = _to_jrj_security_id(code)
    is_weekly = ktype == "week"
    cache_key = f"jrj_{ktype}_{code}_{days}"

    # 周K使用缓存
    if is_weekly:
        cached = cache_get("kline", cache_key)
        if cached and isinstance(cached, list):
            logger.debug("JRJ周K缓存命中: %s", code)
            return [_KlineBar(**b) if isinstance(b, dict) else b for b in cached]

    url = "https://gateway.jrj.com/quot-kline?" + urlencode(
        {
            "format": "json",
            "securityId": secid,
            "type": ktype,
            "direction": "left",
            "range.num": str(days),
        }
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        logger.debug("JRJ %s请求失败: %s - %s", ktype, code, e)
        return []

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

    bars = _parse_jrj_kline(kline, is_weekly=is_weekly)

    # 周K写入缓存
    if is_weekly and bars:
        cache_data = [{"date": b.date, "open": b.open, "close": b.close,
                       "high": b.high, "low": b.low, "volume": b.volume} for b in bars]
        cache_set("kline", cache_key, cache_data, ttl_seconds=_WEEKLY_CACHE_TTL)

    return bars


def _fetch_jrj_daily_kline(code: str, days: int = 150) -> list[_KlineBar]:
    """从金融界获取日K线（主要数据源）。

    JRJ 在 VPS 上可用，作为主要数据源。
    使用 150 天数据可以计算 60 日均线（约 3 个月）。

    Args:
        code: 6位股票代码。
        days: 获取天数。

    Returns:
        日K列表，按日期升序。
    """
    return _fetch_jrj_kline(code, ktype="day", days=days)


def _fetch_jrj_weekly_kline(code: str, weeks: int = 30) -> list[_KlineBar]:
    """从金融界获取周K线。

    用于计算5周均线方向。

    Args:
        code: 6位股票代码。
        weeks: 获取周数。

    Returns:
        周K列表，按日期升序。
    """
    return _fetch_jrj_kline(code, ktype="week", days=weeks)


# 保留东方财富作为后备（如果有网络问题可以尝试）
def _fetch_em_kline(code: str, days: int = 26) -> list[_KlineBar]:
    """从东方财富日 K 接口获取历史 OHLCV（含成交量，单位：手）。

    在中国大陆服务器（VPS）可正常访问；境外环境降级为 JRJ kline
    （无 volume，量能信号自动跳过）。

    Args:
        code: 6位股票代码。
        days: 最多获取条数（含今日可能的未完成 K 线）。

    Returns:
        日 K 列表，按日期升序。出错返回空列表。
    """
    daily_bars = _try_em_kline(code, days)
    if daily_bars:
        return daily_bars
    return _fallback_jrj_kline(code, days)


def _try_em_kline(code: str, days: int) -> list[_KlineBar]:
    """尝试从东方财富获取带 volume 的日 K（失败返回空列表）。"""
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urlencode(
        {
            "secid": _em_secid(code),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": "101",
            "fqt": "0",
            "lmt": str(days),
            "end": "20500101",
        }
    )
    try:
        raw = http_text(url, timeout=10, retries=1)
        data = json.loads(raw)
    except Exception:
        return []

    klines_raw = (data.get("data") or {}).get("klines") or []
    bars: list[_KlineBar] = []
    for k in klines_raw:
        parts = k.split(",")
        if len(parts) < 6:
            continue
        try:
            bars.append(
                _KlineBar(
                    date=parts[0],
                    open=float(parts[1]),
                    close=float(parts[2]),
                    high=float(parts[3]),
                    low=float(parts[4]),
                    volume=float(parts[5]),
                )
            )
        except (ValueError, IndexError):
            continue
    return bars


def _fallback_jrj_kline(code: str, days: int) -> list[_KlineBar]:
    """降级：从金融界日 K 接口获取 OHLC（volume=0，量能信号将被跳过）。"""
    logger.debug("fetch_em_kline 降级到 JRJ kline: %s", code)
    jrj_bars = fetch_jrj_daily_kline(code, range_num=days)
    bars: list[_KlineBar] = []
    for b in jrj_bars:
        t = b.get("time", 0)
        if not t:
            continue
        ts = str(int(t))
        if len(ts) != 8:
            continue
        date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        bars.append(
            _KlineBar(
                date=date_str,
                open=b.get("open", 0.0),
                close=b.get("close", 0.0),
                high=b.get("high", 0.0),
                low=b.get("low", 0.0),
                volume=0.0,  # JRJ kline 无成交量，量能信号自动跳过
            )
        )
    return bars


# ---------------------------------------------------------------------------
# Tencent realtime quote
# ---------------------------------------------------------------------------


@dataclass
class _RealtimeQuote:
    code: str
    name: str
    current: float
    prev_close: float
    open: float
    high: float
    low: float
    volume_lot: float   # 手
    change_pct: float   # %


def _to_tencent_code(code: str) -> str:
    """6位代码 → 腾讯行情前缀（sh/sz）。"""
    return f"sh{code}" if code.startswith("6") else f"sz{code}"


def _fetch_realtime(codes: list[str]) -> dict[str, _RealtimeQuote]:
    """从腾讯行情接口（qt.gtimg.cn）批量获取实时行情。

    Tencent format (tilde-separated fields, as of 2026-02):
        [1]=name [2]=code [3]=current [4]=prev_close [5]=open [6]=volume_lot
        [9-28]=bid/ask 5 levels  [29]=empty  [30]=datetime  [31]=change_amount
        [32]=change_pct%  [33]=high  [34]=low

    Args:
        codes: 6位股票代码列表。

    Returns:
        dict[code, _RealtimeQuote]，解析失败的股票不在结果中。
    """
    if not codes:
        return {}
    query = ",".join(_to_tencent_code(c) for c in codes)
    url = f"http://qt.gtimg.cn/q={query}"
    try:
        # qt.gtimg.cn 返回 GBK 编码，需用 http_bytes 后手动解码
        raw = http_bytes(url, timeout=12, retries=2)
        text = raw.decode("gbk", errors="replace")
    except Exception:
        logger.warning("fetch_realtime 请求失败")
        return {}

    result: dict[str, _RealtimeQuote] = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" not in line or "~" not in line:
            continue
        try:
            inner = line.split("=", 1)[1].strip().strip('";')
            fields = inner.split("~")
            # 腾讯行情格式（实测）:
            #   [3]=current [4]=prev_close [5]=open [6]=volume_lot
            #   [9-28]=bid/ask 5层  [29]=空  [30]=datetime  [31]=涨跌额
            #   [32]=涨跌幅%  [33]=最高  [34]=最低
            if len(fields) < 35:
                continue
            code = fields[2]
            current = float(fields[3]) if fields[3] else 0.0
            prev_close = float(fields[4]) if fields[4] else 0.0
            open_p = float(fields[5]) if fields[5] else 0.0
            volume_lot = float(fields[6]) if fields[6] else 0.0
            # high/low at indices 33/34 — validated against current price range
            raw_high = float(fields[33]) if fields[33] else 0.0
            raw_low = float(fields[34]) if fields[34] else 0.0
            high = raw_high if raw_high >= current > 0 else 0.0
            low = raw_low if 0 < raw_low <= current else 0.0
            change_pct = (
                (current - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
            )
            if current > 0:
                result[code] = _RealtimeQuote(
                    code=code,
                    name=fields[1],
                    current=current,
                    prev_close=prev_close,
                    open=open_p,
                    high=high,
                    low=low,
                    volume_lot=volume_lot,
                    change_pct=change_pct,
                )
        except (ValueError, IndexError):
            continue
    return result


# ---------------------------------------------------------------------------
# Signal analysis
# ---------------------------------------------------------------------------


@dataclass
class StockSignal:
    code: str
    name: str
    signal: str     # "buy_dip" / "watch"
    reason: str
    price: float
    change: float   # change_pct %
    ma5_week: float  # 5周均线
    ma10: float
    ma20: float
    star: int
    score: int


def _compute_star(closes: list[float]) -> int:
    """基于 MA10/MA20 排列估算趋势星级（1–5 星）。

    MA10 显著高于 MA20 → 趋势强劲 → 高星级。
    """
    if len(closes) < 20:
        return 1
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    if ma20 <= 0:
        return 1
    gap_pct = (ma10 - ma20) / ma20 * 100
    if gap_pct >= 3.0:
        return 5
    if gap_pct >= 1.5:
        return 4
    if gap_pct >= 0:
        return 3
    return 2


def _analyze_signal(
    code: str,
    name: str,
    daily_bars: list[_KlineBar],
    weekly_bars: list[_KlineBar],
    rt: _RealtimeQuote,
    sentiment: MarketSentiment,
) -> StockSignal | None:
    """基于5周均线的买入信号分析。

    核心逻辑：趋势股的真正买点在于回调到5周均线附近。
    周线买点比日线更稳定，能过滤掉大部分噪音。
    使用 JRJ 数据源（VPS 可访问）。

    评分规则:
        周线分析:
          当前价 < MA5(周)              → 直接排除（周线趋势破坏）
          当前价在 MA5(周)附近(±3%)     → +50（周线级别回调到位）
          当前价 > MA5(周)              → 持有信号，不加分
        日线辅助:
          当前价 < MA20(日)              → 直接排除
          适度下跌 -3% ~ -6%            → +15
          缩量回调                     → +10
          放量下跌                     → -20
        市场环境:
          黄色市场                     → 门槛提高 15 分

    Returns:
        StockSignal 或 None（不满足最低门槛时）。
    """
    today_str = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d")
    # 只用已完成交易日的历史 K 线，排除今日可能的半日数据
    hist = [b for b in daily_bars if b.date < today_str]
    if len(hist) < 20:
        logger.debug("历史数据不足: %s (%d 条历史 K 线)", code, len(hist))
        return None

    # ──────────────── 周线分析（核心） ────────────────
    if len(weekly_bars) < 5:
        logger.debug("周K数据不足: %s (%d 周)", code, len(weekly_bars))
        # 周K不足时降级为日线判断
        weekly_closes: list[float] = []
        ma5_week = 0.0
    else:
        weekly_closes = [b.close for b in weekly_bars]
        ma5_week = sum(weekly_closes[-5:]) / 5

    current = rt.current
    change_pct = rt.change_pct
    today_vol = rt.volume_lot

    if current <= 0:
        return None

    # ──────────────── 周线核心过滤 ────────────────
    if ma5_week > 0:
        # 周线趋势破坏：跌破5周均线
        if current < ma5_week:
            logger.debug("%s 跌破5周均线(%.2f<%.2f)，周线趋势破坏", code, current, ma5_week)
            return None
        # 5周均线方向验证：均线本身必须向上倾斜（当前MA5W > 3周前MA5W）
        if len(weekly_closes) >= 8:
            ma5w_prev = sum(weekly_closes[-8:-3]) / 5
            if ma5_week <= ma5w_prev:
                logger.debug(
                    "%s 5周均线方向向下(%.2f<=%.2f)，趋势无效",
                    code, ma5_week, ma5w_prev,
                )
                return None
    else:
        # 没有周K数据时，用日线MA20作为后备
        if len(hist) < 20:
            return None

    # ──────────────── 日线分析（辅助） ────────────────
    closes = [b.close for b in hist]
    volumes = [b.volume for b in hist]

    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else 0.0
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0.0
    avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else (
        sum(volumes) / len(volumes) if volumes else 0.0
    )
    star = _compute_star(closes)

    if ma20 <= 0:
        return None

    # 硬排除：价格跌破日线 MA20（趋势破坏）
    if current < ma20:
        return None

    score = 0
    reasons: list[str] = []

    # ──────────────── 周线评分（核心，只认回调买点） ────────────────
    # 关键：只有回调到5周均线附近才是买点！
    # 价格在5周均线之上是"持有"信号，不是"买入"信号
    if ma5_week > 0:
        week_deviation = (current - ma5_week) / ma5_week * 100
        if abs(week_deviation) <= 3.0:
            # 回调到5周均线附近（±3%），这是周线级别的最佳买点
            score += 50
            reasons.append(f"回调至5周均线({week_deviation:+.1f}%)")
        elif current > ma5_week:
            # 价格在5周均线之上，这是"持有"信号，不给买入加分
            reasons.append("周线趋势完好（持有）")
    else:
        # 没有周K时，用日线MA10作为后备（同样只认回调）
        if ma10 > 0 and ma20 > 0:
            if ma20 <= current < ma10:
                score += 30
                reasons.append("回调至MA10附近")
            elif current >= ma10:
                # 价格在MA10之上，不给买入加分
                reasons.append("价格在MA10之上（持有）")

    # ──────────────── 日线辅助评分 ────────────────
    # 成交量对比
    if avg_vol_20 > 0:
        vol_ratio = today_vol / avg_vol_20
        if vol_ratio < 0.7:
            score += 10
            reasons.append("缩量回调")
        elif vol_ratio > 1.5 and change_pct < -2.0:
            score -= 20
            reasons.append("放量下跌")

    # 涨跌幅：适度下跌是低吸机会
    if -6.0 <= change_pct <= -3.0:
        score += 15
        reasons.append(f"适度下跌({change_pct:.1f}%)")
    elif change_pct < -8.0:
        score -= 15
        reasons.append("跌幅过大")

    # 趋势星级
    if star >= 4:
        score += 10

    # ──────────────── 门槛设置 ────────────────
    threshold_bonus = 15 if sentiment.danger_level == "yellow" else 0
    threshold_buy = 45 + threshold_bonus  # 只有回调到5周均线附近才能触发
    threshold_watch = 25 + threshold_bonus

    reason_str = "，".join(reasons) if reasons else "观察中"

    if score >= threshold_buy:
        signal_type = "buy_dip"
    elif score >= threshold_watch:
        signal_type = "watch"
    else:
        return None

    return StockSignal(
        code=code,
        name=name,
        signal=signal_type,
        reason=reason_str,
        price=round(current, 3),
        change=round(change_pct, 2),
        ma5_week=round(ma5_week, 3) if ma5_week > 0 else 0.0,
        ma10=round(ma10, 3),
        ma20=round(ma20, 3),
        star=star,
        score=score,
    )


def _check_exit_signals(
    holdings: list[dict[str, Any]],
    kline_map: dict[str, tuple[str, list[_KlineBar], list[_KlineBar]]],
) -> list[StockSignal]:
    """检查持仓股是否触发出场信号。

    Args:
        holdings: broker_account hold_list，每项含 code / name / hold_vol。
        kline_map: 已拉取的 K 线数据映射（可能不含全部持仓）。

    Returns:
        触发出场条件的 StockSignal 列表。signal 值为
        "stop_loss" 或 "take_profit_partial"。
    """
    today_str = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d")
    exits: list[StockSignal] = []

    for h in holdings:
        code = str(h.get("code", "")).strip()
        hold_vol = int(h.get("hold_vol", 0) or 0)
        if hold_vol <= 0 or not code:
            continue
        entry = kline_map.get(code)
        if entry is None:
            continue
        name, daily_bars, weekly_bars = entry
        if len(weekly_bars) < 5:
            continue

        weekly_closes = [b.close for b in weekly_bars]
        ma5_week = sum(weekly_closes[-5:]) / 5
        if ma5_week <= 0:
            continue

        hist = [b for b in daily_bars if b.date < today_str]
        if not hist:
            continue
        current = hist[-1].close

        if current < ma5_week:
            exits.append(
                StockSignal(
                    code=code,
                    name=name,
                    signal="stop_loss",
                    reason="收盘跌破5周均线",
                    price=round(current, 3),
                    change=0.0,
                    ma5_week=round(ma5_week, 3),
                    ma10=0.0,
                    ma20=0.0,
                    star=0,
                    score=0,
                )
            )
        elif current > ma5_week * 1.25:
            pct = (current / ma5_week - 1) * 100
            exits.append(
                StockSignal(
                    code=code,
                    name=name,
                    signal="take_profit_partial",
                    reason=f"超涨{pct:.0f}%，建议减仓50%",
                    price=round(current, 3),
                    change=0.0,
                    ma5_week=round(ma5_week, 3),
                    ma10=0.0,
                    ma20=0.0,
                    star=0,
                    score=0,
                )
            )

    return exits


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _write_signals(
    signals: list[StockSignal],
    watched: list[StockSignal],
    sentiment: MarketSentiment,
    *,
    exits: list[StockSignal] | None = None,
) -> None:
    """将信号结果覆盖写入 signals/watchlist_signals.json。"""
    _SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    scanned_at = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    output = {
        "scanned_at": scanned_at,
        "market": {
            "limit_up": sentiment.limit_up,
            "limit_down": sentiment.limit_down,
            "danger_level": sentiment.danger_level,
        },
        "signals": [asdict(s) for s in signals],
        "watched": [asdict(s) for s in watched],
        "exits": [asdict(s) for s in (exits or [])],
    }
    with open(_SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(
        "信号文件已写入: %s（buy_dip=%d, watch=%d, exits=%d）",
        _SIGNALS_FILE,
        len(signals),
        len(watched),
        len(exits or []),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI 入口：扫描 watchlist 盘中信号。"""
    parser = argparse.ArgumentParser(description="Watchlist 盘中信号扫描")
    parser.add_argument("--verbose", action="store_true", help="详细日志输出")
    parser.add_argument(
        "--force", action="store_true", help="忽略交易时间限制（调试用）"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if not args.force and not _is_trading_time():
        now_str = datetime.now(tz=_CN_TZ).strftime("%H:%M")
        logger.info("非交易时段（%s），跳过扫描", now_str)
        return

    config = _load_app_config()
    ths_cookie: str | None = config.get("ths_cookie") or None

    # ── 1. 市场情绪 ────────────────────────────────────────────────────────
    logger.info("获取市场情绪...")
    sentiment = fetch_market_sentiment(ths_cookie)
    logger.info(
        "市场情绪: 涨停=%d, 跌停=%d, 等级=%s",
        sentiment.limit_up,
        sentiment.limit_down,
        sentiment.danger_level,
    )

    # THS 明确报告市场未开盘（节假日 / 盘后）→ 跳过，避免基于昨日收盘价产生虚假信号
    if not args.force and not sentiment.market_open and sentiment.danger_level != "unknown":
        logger.info("THS 报告市场未开盘（%s），跳过扫描", sentiment.danger_level)
        return

    if sentiment.danger_level == "red":
        logger.warning("市场高压线（跌停 >= 80），中止扫描，写空信号文件")
        _write_signals([], [], sentiment)
        return

    # ── 2. 加载 watchlist ──────────────────────────────────────────────────
    stocks = load_watchlist()
    active = [s for s in stocks if s.get("status") == "active"]
    if not active:
        logger.info("watchlist 中无 active 股票，退出")
        _write_signals([], [], sentiment)
        return

    logger.info("扫描 watchlist: %d 只 active 股", len(active))

    # ── 2b. 加载当前持仓（用于出场信号） ───────────────────────────��────────────────
    try:
        from ashare_data.fetchers.broker_account import fetch_broker_account
        broker_data = fetch_broker_account()
        holdings: list[dict[str, Any]] = broker_data.get("hold_list", [])
        active_holdings = [h for h in holdings if int(h.get("hold_vol", 0) or 0) > 0]
        logger.info("持仓股数量: %d", len(active_holdings))
    except Exception as exc:
        logger.warning("持仓数据获取失败（出场信号将跳过）: %s", exc)
        holdings = []

    # ── 3. 并发拉取东方财富日 K ────────────────────────────────────────────
    def _fetch_kline_job(
        stock: dict[str, Any],
    ) -> tuple[str, str, list[_KlineBar], list[_KlineBar]]:
        code = stock["code"]
        name = stock.get("name", code)
        # 使用 JRJ 数据源（VPS 可访问）
        bars = _fetch_jrj_daily_kline(code, days=150)
        weekly_bars = _fetch_jrj_weekly_kline(code, weeks=30)
        return code, name, bars, weekly_bars

    kline_map: dict[str, tuple[str, list[_KlineBar], list[_KlineBar]]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(active))) as pool:
        futures = [pool.submit(_fetch_kline_job, s) for s in active]
        for fut in futures:
            try:
                code, name, bars, weekly_bars = fut.result()
                kline_map[code] = (name, bars, weekly_bars)
            except Exception as exc:
                logger.warning("K 线获取异常: %s", exc)

    # ── 3b. 为持仓中不在 watchlist 的股票补充 K 线 ─────────────────────────
    holding_codes_extra = [
        h for h in holdings
        if str(h.get("code", "")) not in kline_map
        and int(h.get("hold_vol", 0) or 0) > 0
    ]
    if holding_codes_extra:
        extra_stocks = [
            {"code": h["code"], "name": h.get("name", h["code"])}
            for h in holding_codes_extra
        ]
        with ThreadPoolExecutor(max_workers=min(8, len(extra_stocks))) as pool:
            extra_futures = [pool.submit(_fetch_kline_job, s) for s in extra_stocks]
            for fut in extra_futures:
                try:
                    code, name, bars, weekly_bars = fut.result()
                    kline_map[code] = (name, bars, weekly_bars)
                except Exception as exc:
                    logger.warning("持仓 K 线获取异常: %s", exc)

    # ── 4. 批量获取腾讯实时行情 ───────────────────────────────────────────
    codes = list(kline_map.keys())
    realtime_map = _fetch_realtime(codes)
    logger.info("实时行情获取: %d/%d 只", len(realtime_map), len(codes))

    # ── 5. 计算信号 ────────────────────────────────────────────────────────
    buy_signals: list[StockSignal] = []
    watch_signals: list[StockSignal] = []

    for code, (name, bars, weekly_bars) in kline_map.items():
        rt = realtime_map.get(code)
        if rt is None:
            logger.debug("实时行情缺失: %s", code)
            continue
        sig = _analyze_signal(code, name, bars, weekly_bars, rt, sentiment)
        if sig is None:
            continue
        if sig.signal == "buy_dip":
            buy_signals.append(sig)
        else:
            watch_signals.append(sig)

    buy_signals.sort(key=lambda s: -s.score)
    watch_signals.sort(key=lambda s: -s.score)

    # ── 5b. 计算出场信号 ───────────────────────────────────────────────────
    exit_signals = _check_exit_signals(holdings, kline_map)
    if exit_signals:
        logger.info("出场信号: %s", [(s.name, s.signal) for s in exit_signals])

    # ── 6. 写文件 ──────────────────────────────────────────────────────────
    _write_signals(buy_signals, watch_signals, sentiment, exits=exit_signals)
    logger.info("扫描完成: buy_dip=%d, watch=%d, exits=%d", len(buy_signals), len(watch_signals), len(exit_signals))


if __name__ == "__main__":
    main()
