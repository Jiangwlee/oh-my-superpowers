#!/usr/bin/env python3
"""Live monitor for sentiment, sectors, and buy targets.

Purpose: Continuously monitor market sentiment, sector flow, and post-close buy
         targets in a terminal dashboard.
Input:   post_close_decisions.json and Tencent/JRJ/THS APIs.
Output:  TUI in terminal + ~/.ashare-assistant/signals/watchlist_signals.json.

Public API:
    main()       -- CLI entry (default: continuous watch loop)
    scan_once()  -- execute one scan and return render snapshot
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ashare_data.core.config import ASHARE_HOME, BROKER_DIR
from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.governance import load_latest_run_id
from ashare_data.core.http_client import http_bytes, http_text
from ashare_data.core.utils import atomic_write_json
from ashare_data.core.utils import norm_price as _norm_price
from ashare_data.fetchers.market_overview import fetch_market_sectors_top_n
from ashare_data.fetchers.trend_scanner import fetch_jrj_daily_kline
from ashare_data.fetchers.market_sentiment import MarketSentiment, fetch_market_sentiment

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))
_SIGNALS_DIR = ASHARE_HOME / "signals"
_SIGNALS_FILE = _SIGNALS_DIR / "watchlist_signals.json"
_POST_CLOSE_FILE = _SIGNALS_DIR / "post_close_decisions.json"
_CONFIG_FILE = ASHARE_HOME / "config.json"
_PULLBACK_STATE_FILE = ASHARE_HOME / "memory" / "pullback_state.json"
_POSITIONS_DIR = BROKER_DIR / "positions"
_CONSOLE = Console()

_DEFAULT_SIGNAL_PARAMS: dict[str, float] = {
    "dev5w_band": 0.03,
    "vr20d_shrink": 0.80,
    "vr20d_expand": 1.10,
    "intraday_break_allow": 0.02,
    "ma5w_break_week": 0.015,
    "fast_stop_pct": 0.04,
    "pb_breakout_buffer": 0.003,
    "dev20w_no_add": 0.20,
    "dev20w_no_trade": 0.25,
    "position_base": 0.25,
    "position_yellow": 0.15,
    "drawdown20_max": 0.12,
}
_SIGNALS_SCHEMA_VERSION = "1.0"

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


def _load_signal_params(config: dict[str, Any]) -> dict[str, float]:
    """加载并归一化信号参数。"""
    raw = config.get("watchlist_monitor")
    source = raw if isinstance(raw, dict) else config
    params = dict(_DEFAULT_SIGNAL_PARAMS)
    for key, default_value in _DEFAULT_SIGNAL_PARAMS.items():
        value = source.get(key) if isinstance(source, dict) else None
        if value is None:
            continue
        try:
            params[key] = float(value)
        except (TypeError, ValueError):
            logger.warning("参数 %s 非法，使用默认值 %.4f", key, default_value)
    return params


def _load_pullback_state() -> dict[str, dict[str, Any]]:
    """读取回撤状态文件。"""
    if not _PULLBACK_STATE_FILE.exists():
        return {}
    try:
        with open(_PULLBACK_STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for code, state in data.items():
            if isinstance(code, str) and isinstance(state, dict):
                normalized[code] = state
        return normalized
    except Exception:
        logger.exception("读取 pullback_state.json 失败，使用空状态")
        return {}


def _save_pullback_state(state_map: dict[str, dict[str, Any]]) -> None:
    """写入回撤状态文件。"""
    _PULLBACK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(_PULLBACK_STATE_FILE, state_map)


def _is_buy_action(value: Any) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return False
    if raw in {"open", "add", "buy", "entry", "buy_open_t1"}:
        return True
    return raw.startswith("buy")


def _load_post_close_buy_targets() -> tuple[list[dict[str, str]], dict[str, Any]]:
    """读取 post_close_decisions.json 中触发买入动作的个股。"""
    if not _POST_CLOSE_FILE.exists():
        return [], {"source_run_id": load_latest_run_id(), "source_files": []}
    try:
        payload = json.loads(_POST_CLOSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("读取 post_close_decisions.json 失败")
        return [], {"source_run_id": load_latest_run_id(), "source_files": ["signals/post_close_decisions.json"]}
    rows = payload.get("decisions", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return [], {"source_run_id": load_latest_run_id(), "source_files": ["signals/post_close_decisions.json"]}

    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_buy_action(row.get("action")):
            continue
        code = str(row.get("code", "")).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        targets.append({"code": code, "name": str(row.get("name", code))})
    source_run_id = load_latest_run_id()
    if isinstance(payload, dict):
        source_run_id = str(payload.get("source_run_id") or source_run_id)
    return targets, {"source_run_id": source_run_id, "source_files": ["signals/post_close_decisions.json"]}


def _load_latest_holdings_snapshot() -> tuple[str, list[dict[str, Any]]]:
    """读取最新可用收盘持仓快照。"""
    if not _POSITIONS_DIR.exists():
        return "", []
    files = sorted(
        [p for p in _POSITIONS_DIR.glob("*.json") if p.is_file()],
        key=lambda p: p.stem,
    )
    if not files:
        return "", []
    target = files[-1]
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("读取持仓快照失败: %s", target)
        return "", []
    rows = payload.get("hold_list", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return target.stem, []
    active = [r for r in rows if isinstance(r, dict) and int(r.get("hold_vol", 0) or 0) > 0]
    return target.stem, active


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
    state: str
    reason: str
    price: float
    change: float
    ma5w: float
    ma20w: float
    ma20d: float
    vr20d: float
    dev20w: float
    dev5w: float
    pb_start_date: str
    pb_high: float
    pb_low: float
    entry_price: float
    stop_price: float
    position_target: float
    action_next_day: str
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


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _build_signal(
    *,
    code: str,
    name: str,
    state: str,
    reason: str,
    rt: _RealtimeQuote,
    ma5w: float,
    ma20w: float,
    ma20d: float,
    vr20d: float,
    dev20w: float,
    dev5w: float,
    pb_start_date: str = "",
    pb_high: float = 0.0,
    pb_low: float = 0.0,
    entry_price: float = 0.0,
    stop_price: float = 0.0,
    position_target: float = 0.0,
    action_next_day: str = "hold",
    score: int = 0,
) -> StockSignal:
    return StockSignal(
        code=code,
        name=name,
        state=state,
        reason=reason,
        price=round(rt.current, 3),
        change=round(rt.change_pct, 2),
        ma5w=round(ma5w, 3),
        ma20w=round(ma20w, 3),
        ma20d=round(ma20d, 3),
        vr20d=round(vr20d, 3),
        dev20w=round(dev20w, 4),
        dev5w=round(dev5w, 4),
        pb_start_date=pb_start_date,
        pb_high=round(pb_high, 3),
        pb_low=round(pb_low, 3),
        entry_price=round(entry_price, 3),
        stop_price=round(stop_price, 3),
        position_target=round(position_target, 3),
        action_next_day=action_next_day,
        score=score,
    )


def _analyze_signal(
    code: str,
    name: str,
    daily_bars: list[_KlineBar],
    weekly_bars: list[_KlineBar],
    rt: _RealtimeQuote,
    sentiment: MarketSentiment,
    params: dict[str, float] | None = None,
    setup_state: dict[str, Any] | None = None,
) -> tuple[StockSignal | None, dict[str, Any] | None]:
    """基于 SETUP/ENTRY 状态机输出交易信号。"""
    using_params = params or _DEFAULT_SIGNAL_PARAMS
    today_str = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d")
    hist = [b for b in daily_bars if b.date < today_str]
    if len(hist) < 25 or len(weekly_bars) < 20 or rt.current <= 0:
        return None, None

    closes = [b.close for b in hist]
    volumes = [b.volume for b in hist]
    weekly_closes = [b.close for b in weekly_bars]

    ma20d = _mean(closes[-20:])
    ma20d_prev5 = _mean(closes[-25:-5])
    ma5w = _mean(weekly_closes[-5:])
    ma5w_prev3 = _mean(weekly_closes[-8:-3])
    ma20w = _mean(weekly_closes[-20:])
    if min(ma20d, ma20d_prev5, ma5w, ma5w_prev3, ma20w) <= 0:
        return None, None

    close_w = weekly_closes[-1]
    if rt.current <= ma20d or ma20d <= ma20d_prev5 or close_w <= ma5w or ma5w <= ma5w_prev3:
        return None, None

    avg_vol_20 = _mean(volumes[-20:])
    vr20d = rt.volume_lot / avg_vol_20 if avg_vol_20 > 0 else 0.0
    dev5w = (rt.current - ma5w) / ma5w
    dev20w = (rt.current - ma20w) / ma20w
    highest_close_20 = max(closes[-20:])
    drawdown20 = (
        (highest_close_20 - rt.current) / highest_close_20 if highest_close_20 > 0 else 0.0
    )

    pb_high_rt = rt.high if rt.high > 0 else rt.current
    pb_low_rt = rt.low if rt.low > 0 else rt.current
    position_target = (
        using_params["position_yellow"]
        if sentiment.danger_level == "yellow"
        else using_params["position_base"]
    )

    setup_condition = (
        abs(dev5w) <= using_params["dev5w_band"]
        and (drawdown20 <= using_params["drawdown20_max"] or rt.current >= ma20d)
        and vr20d <= using_params["vr20d_shrink"]
        and rt.current >= ma5w * (1 - using_params["intraday_break_allow"])
        and dev20w <= using_params["dev20w_no_trade"]
    )

    if setup_condition:
        old_high = float((setup_state or {}).get("pb_high") or pb_high_rt)
        old_low = float((setup_state or {}).get("pb_low") or pb_low_rt)
        next_state = {
            "pb_start_date": str((setup_state or {}).get("pb_start_date") or today_str),
            "pb_high": max(old_high, pb_high_rt),
            "pb_low": min(old_low, pb_low_rt),
            "updated_at": datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        }
        return (
            _build_signal(
                code=code,
                name=name,
                state="SETUP",
                reason="回撤进入观察区，等待突破PB_HIGH确认",
                rt=rt,
                ma5w=ma5w,
                ma20w=ma20w,
                ma20d=ma20d,
                vr20d=vr20d,
                dev20w=dev20w,
                dev5w=dev5w,
                pb_start_date=next_state["pb_start_date"],
                pb_high=next_state["pb_high"],
                pb_low=next_state["pb_low"],
                position_target=position_target,
                action_next_day="observe_setup",
                score=70,
            ),
            next_state,
        )

    if setup_state:
        prev_pb_high = float(setup_state.get("pb_high") or pb_high_rt)
        prev_pb_low = float(setup_state.get("pb_low") or pb_low_rt)
        next_state = {
            "pb_start_date": str(setup_state.get("pb_start_date") or today_str),
            "pb_high": max(prev_pb_high, pb_high_rt),
            "pb_low": min(prev_pb_low, pb_low_rt),
            "updated_at": datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        }
        trigger_condition = (
            rt.current > prev_pb_high * (1 + using_params["pb_breakout_buffer"])
            and vr20d >= using_params["vr20d_expand"]
            and rt.current > rt.open
            and dev20w <= using_params["dev20w_no_trade"]
        )
        if trigger_condition:
            stop1 = rt.current * (1 - using_params["fast_stop_pct"])
            stop2 = next_state["pb_low"] * 0.99
            stop_price = max(stop1, stop2)
            return (
                _build_signal(
                    code=code,
                    name=name,
                    state="ENTRY",
                    reason="突破PB_HIGH且量能回归，触发确认入场",
                    rt=rt,
                    ma5w=ma5w,
                    ma20w=ma20w,
                    ma20d=ma20d,
                    vr20d=vr20d,
                    dev20w=dev20w,
                    dev5w=dev5w,
                    pb_start_date=next_state["pb_start_date"],
                    pb_high=next_state["pb_high"],
                    pb_low=next_state["pb_low"],
                    entry_price=rt.current,
                    stop_price=stop_price,
                    position_target=position_target,
                    action_next_day="buy_open_t1",
                    score=95,
                ),
                None,
            )
        return (
            _build_signal(
                code=code,
                name=name,
                state="HOLD",
                reason="已在回撤观察阶段，等待突破确认",
                rt=rt,
                ma5w=ma5w,
                ma20w=ma20w,
                ma20d=ma20d,
                vr20d=vr20d,
                dev20w=dev20w,
                dev5w=dev5w,
                pb_start_date=next_state["pb_start_date"],
                pb_high=next_state["pb_high"],
                pb_low=next_state["pb_low"],
                position_target=0.0,
                action_next_day="wait_breakout",
                score=55,
            ),
            next_state,
        )

    if dev20w > using_params["dev20w_no_trade"]:
        return (
            _build_signal(
                code=code,
                name=name,
                state="HOLD",
                reason="周线乖离过大，进入加速区禁止开仓",
                rt=rt,
                ma5w=ma5w,
                ma20w=ma20w,
                ma20d=ma20d,
                vr20d=vr20d,
                dev20w=dev20w,
                dev5w=dev5w,
                position_target=0.0,
                action_next_day="no_new_position",
                score=40,
            ),
            None,
        )

    return (
        _build_signal(
            code=code,
            name=name,
            state="HOLD",
            reason="趋势完整，等待回撤进入SETUP",
            rt=rt,
            ma5w=ma5w,
            ma20w=ma20w,
            ma20d=ma20d,
            vr20d=vr20d,
            dev20w=dev20w,
            dev5w=dev5w,
            position_target=0.0,
            action_next_day="wait_pullback",
            score=35,
        ),
        None,
    )


def _check_exit_signals(
    holdings: list[dict[str, Any]],
    kline_map: dict[str, tuple[str, list[_KlineBar], list[_KlineBar]]],
    params: dict[str, float],
) -> list[StockSignal]:
    """检查持仓股是否触发 REDUCE/EXIT。"""
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

        ma20w = _mean(weekly_closes[-20:]) if len(weekly_closes) >= 20 else 0.0
        if ma20w <= 0:
            continue

        hist = [b for b in daily_bars if b.date < today_str]
        if not hist:
            continue
        current = hist[-1].close
        rt = _RealtimeQuote(
            code=code,
            name=name,
            current=current,
            prev_close=current,
            open=current,
            high=current,
            low=current,
            volume_lot=0.0,
            change_pct=0.0,
        )

        dev20w = (current - ma20w) / ma20w
        dev5w = (current - ma5_week) / ma5_week
        close_w = weekly_closes[-1]

        prev_week_break = False
        if len(weekly_closes) >= 6:
            prev_ma5w = _mean(weekly_closes[-6:-1])
            prev_week_close = weekly_closes[-2]
            prev_week_break = prev_week_close < prev_ma5w * (1 - params["ma5w_break_week"])

        this_week_break = close_w < ma5_week * (1 - params["ma5w_break_week"])
        if this_week_break and prev_week_break:
            exits.append(
                _build_signal(
                    code=code,
                    name=name,
                    state="EXIT",
                    reason="连续两周有效跌破5周线，执行清仓",
                    rt=rt,
                    ma5w=ma5_week,
                    ma20w=ma20w,
                    ma20d=0.0,
                    vr20d=0.0,
                    dev20w=dev20w,
                    dev5w=dev5w,
                    action_next_day="sell_all_open_t1",
                    score=100,
                )
            )
            continue

        if this_week_break:
            exits.append(
                _build_signal(
                    code=code,
                    name=name,
                    state="REDUCE",
                    reason="周线有效跌破5周线，先减仓50%",
                    rt=rt,
                    ma5w=ma5_week,
                    ma20w=ma20w,
                    ma20d=0.0,
                    vr20d=0.0,
                    dev20w=dev20w,
                    dev5w=dev5w,
                    action_next_day="sell_half_open_t1",
                    score=85,
                )
            )

        entry_price = float(
            h.get("cost_price")
            or h.get("buy_price")
            or h.get("price")
            or 0.0
        )
        if entry_price > 0:
            stop_price = entry_price * (1 - params["fast_stop_pct"])
            if current < stop_price:
                exits.append(
                    _build_signal(
                        code=code,
                        name=name,
                        state="EXIT",
                        reason=f"触发快速止损({params['fast_stop_pct']:.0%})",
                        rt=rt,
                        ma5w=ma5_week,
                        ma20w=ma20w,
                        ma20d=0.0,
                        vr20d=0.0,
                        dev20w=dev20w,
                        dev5w=dev5w,
                        entry_price=entry_price,
                        stop_price=stop_price,
                        action_next_day="sell_all_open_t1",
                        score=95,
                    )
                )
                continue

        if current > ma5_week * 1.25 or dev20w > 0.30:
            exits.append(
                _build_signal(
                    code=code,
                    name=name,
                    state="REDUCE",
                    reason="周线超涨/乖离过大，执行减仓50%",
                    rt=rt,
                    ma5w=ma5_week,
                    ma20w=ma20w,
                    ma20d=0.0,
                    vr20d=0.0,
                    dev20w=dev20w,
                    dev5w=dev5w,
                    action_next_day="sell_half_open_t1",
                    score=75,
                )
            )

    return exits


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _write_signals(
    signals: list[StockSignal],
    sentiment: MarketSentiment,
    *,
    exits: list[StockSignal] | None = None,
    pullback_states: dict[str, dict[str, Any]] | None = None,
    sectors: dict[str, Any] | None = None,
    monitored: dict[str, int] | None = None,
    holdings_live: list[dict[str, Any]] | None = None,
    holdings_source_date: str = "",
    source_run_id: str = "",
    source_files: list[str] | None = None,
) -> None:
    """将信号结果覆盖写入 signals/watchlist_signals.json。"""
    _SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    scanned_at = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    output = {
        "schema_version": _SIGNALS_SCHEMA_VERSION,
        "scanned_at": scanned_at,
        "market": {
            "limit_up": sentiment.limit_up,
            "limit_down": sentiment.limit_down,
            "danger_level": sentiment.danger_level,
        },
        "market_sectors": sectors or {},
        "monitored": monitored or {},
        "holdings_source_date": holdings_source_date,
        "holdings_live": holdings_live or [],
        "source_run_id": source_run_id or load_latest_run_id(),
        "source_files": source_files or [],
        "signals": [asdict(s) for s in signals],
        "exits": [asdict(s) for s in (exits or [])],
        "pullback_state_count": len(pullback_states or {}),
    }
    atomic_write_json(_SIGNALS_FILE, output)
    logger.info(
        "信号文件已写入: %s（signals=%d, exits=%d）",
        _SIGNALS_FILE,
        len(signals),
        len(exits or []),
    )


def _danger_emoji(level: str) -> str:
    if level == "red":
        return "🔴"
    if level == "yellow":
        return "🟡"
    if level == "green":
        return "🟢"
    return "⚪"


def _danger_style(level: str) -> str:
    if level == "red":
        return "bold red"
    if level == "yellow":
        return "bold yellow"
    if level == "green":
        return "bold green"
    return "bold cyan"


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_yi(value: float) -> str:
    return f"{value / 100000000:.2f}亿"


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_holdings_live(
    holdings: list[dict[str, Any]],
    realtime_map: dict[str, _RealtimeQuote],
    kline_map: dict[str, tuple[str, list[_KlineBar], list[_KlineBar]]],
) -> list[dict[str, Any]]:
    """基于持仓快照 + 实时行情构建持仓实时视图。"""
    rows: list[dict[str, Any]] = []
    for item in holdings:
        code = str(item.get("code", "")).strip()
        if not code:
            continue
        rt = realtime_map.get(code)
        entry = kline_map.get(code)
        name = str(item.get("name", "")) or (entry[0] if entry else code)
        hold_vol = int(_safe_float(item.get("hold_vol", 0)))
        if hold_vol <= 0:
            continue

        cost_price = _safe_float(item.get("cost_price") or item.get("buy_price") or item.get("price"))
        current = rt.current if rt is not None else (entry[1][-1].close if entry and entry[1] else 0.0)
        prev_close = rt.prev_close if rt is not None else (entry[1][-1].close if entry and entry[1] else current)
        change_pct = (
            rt.change_pct if rt is not None else ((current - prev_close) / prev_close * 100 if prev_close > 0 else 0.0)
        )

        market_value = current * hold_vol
        cost_value = cost_price * hold_vol if cost_price > 0 else 0.0
        pnl = market_value - cost_value if cost_value > 0 else 0.0
        pnl_pct = (pnl / cost_value * 100.0) if cost_value > 0 else 0.0

        rows.append(
            {
                "code": code,
                "name": name,
                "hold_vol": hold_vol,
                "cost_price": round(cost_price, 3),
                "price": round(current, 3),
                "change_pct": round(change_pct, 2),
                "market_value": round(market_value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            }
        )
    rows.sort(key=lambda x: x["pnl_pct"], reverse=True)
    return rows


def _render_signal_table(signals: list[dict[str, Any]]) -> Table:
    table = Table(title="🔥 买入候选(Top10)", expand=True)
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("State", style="magenta", no_wrap=True)
    table.add_column("Price", justify="right", style="green", no_wrap=True)
    table.add_column("DEV20W", justify="right", style="yellow", no_wrap=True)
    if not signals:
        table.add_row("-", "无", "-", "-", "-")
        return table
    for item in signals[:10]:
        table.add_row(
            str(item.get("code", "")),
            str(item.get("name", "")),
            str(item.get("state", "")),
            f"{float(item.get('price', 0.0)):.2f}",
            _fmt_pct(float(item.get("dev20w", 0.0))),
        )
    return table


def _render_holdings_table(holdings_live: list[dict[str, Any]]) -> Table:
    table = Table(title="💼 持仓实时(收盘持仓 + 实时行情)", expand=True)
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Qty", justify="right", style="magenta", no_wrap=True)
    table.add_column("Cost", justify="right", style="dim", no_wrap=True)
    table.add_column("Price", justify="right", style="green", no_wrap=True)
    table.add_column("Chg%", justify="right", style="yellow", no_wrap=True)
    table.add_column("PnL%", justify="right", style="bold", no_wrap=True)
    table.add_column("MktValue", justify="right", style="blue", no_wrap=True)
    if not holdings_live:
        table.add_row("-", "无", "-", "-", "-", "-", "-", "-")
        return table
    for row in holdings_live[:12]:
        pnl_pct = float(row.get("pnl_pct", 0.0))
        pnl_style = "bold green" if pnl_pct >= 0 else "bold red"
        table.add_row(
            str(row.get("code", "")),
            str(row.get("name", "")),
            str(row.get("hold_vol", 0)),
            f"{float(row.get('cost_price', 0.0)):.2f}",
            f"{float(row.get('price', 0.0)):.2f}",
            f"{float(row.get('change_pct', 0.0)):.2f}%",
            Text(f"{pnl_pct:.2f}%", style=pnl_style),
            _fmt_yi(float(row.get("market_value", 0.0))),
        )
    return table


def _render_exit_table(exits: list[dict[str, Any]]) -> Table:
    table = Table(title="🛡 出场信号(Top10)", expand=True)
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("State", style="red", no_wrap=True)
    table.add_column("Next Action", style="yellow", no_wrap=True)
    if not exits:
        table.add_row("-", "无", "-", "-")
        return table
    for item in exits[:10]:
        table.add_row(
            str(item.get("code", "")),
            str(item.get("name", "")),
            str(item.get("state", "")),
            str(item.get("action_next_day", "")),
        )
    return table


def _render_sector_table(snapshot: dict[str, Any]) -> Table:
    table = Table(title="🏭 板块资金流 Top5（单位：亿）", expand=True)
    table.add_column("Rank", justify="right", style="dim", no_wrap=True)
    table.add_column("Inflow Sector", style="green")
    table.add_column("Inflow", justify="right", style="green", no_wrap=True)
    table.add_column("Outflow Sector", style="red")
    table.add_column("Outflow", justify="right", style="red", no_wrap=True)
    sectors = snapshot.get("market_sectors", {})
    inflow = sectors.get("top_inflow", []) if isinstance(sectors, dict) else []
    outflow = sectors.get("top_outflow", []) if isinstance(sectors, dict) else []
    max_len = max(min(5, len(inflow)), min(5, len(outflow)))
    if max_len == 0:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for idx in range(max_len):
        in_sec = inflow[idx] if idx < len(inflow) and isinstance(inflow[idx], dict) else {}
        out_sec = outflow[idx] if idx < len(outflow) and isinstance(outflow[idx], dict) else {}
        table.add_row(
            str(idx + 1),
            str(in_sec.get("name", "-")),
            _fmt_yi(float(in_sec.get("total_netin", 0.0))) if in_sec else "-",
            str(out_sec.get("name", "-")),
            _fmt_yi(float(out_sec.get("total_netin", 0.0))) if out_sec else "-",
        )
    return table


def _render_tui(snapshot: dict[str, Any], *, clear_screen: bool = True) -> None:
    if clear_screen:
        _CONSOLE.clear()
    now_str = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    title = Text("AShare Live Monitor", style="bold cyan")
    title.append(f"  {now_str}", style="dim")

    market = snapshot.get("market", {})
    level = str(market.get("danger_level", "unknown"))
    summary = Text()
    summary.append(f"涨停 {market.get('limit_up', 0)} | 跌停 {market.get('limit_down', 0)} | 情绪 ", style="white")
    summary.append(f"{_danger_emoji(level)} {level}", style=_danger_style(level))

    monitored = snapshot.get("monitored", {})
    monitor_text = Text(
        f"监控池: 买入信号 {monitored.get('buy_targets', 0)} | "
        f"合计 {monitored.get('universe', 0)}",
        style="white",
    )

    status = str(snapshot.get("status", "ok"))
    message = str(snapshot.get("message", ""))
    if status == "skipped":
        status_line = Text(f"⏸ 跳过扫描: {message}", style="bold yellow")
    elif status == "error":
        status_line = Text(f"❌ 扫描异常: {message}", style="bold red")
    else:
        status_line = Text("✅ 监控运行中", style="bold green")

    signals = snapshot.get("signals", [])
    header = Panel(
        Text.assemble(title, "\n", status_line, "\n", summary, "\n", monitor_text),
        border_style="cyan",
    )
    content = Columns([_render_signal_table(signals), _render_sector_table(snapshot)], equal=True, expand=True)
    footer = Text("Ctrl+C 退出监控", style="dim")
    _CONSOLE.print(header)
    _CONSOLE.print(content)
    _CONSOLE.print(footer)


def scan_once(*, force: bool = False) -> dict[str, Any]:
    """执行一次扫描并返回可渲染快照。

    Args:
        force: 忽略交易时间限制。

    Returns:
        扫描快照 dict，包含 status/market/signals 等字段。
    """
    return _scan_once(force=force)


def _scan_once(*, force: bool = False) -> dict[str, Any]:
    """执行一次扫描并返回可渲染快照。"""
    snapshot: dict[str, Any] = {
        "status": "ok",
        "message": "",
        "market": {},
        "market_sectors": {},
        "monitored": {"buy_targets": 0, "universe": 0},
        "signals": [],
    }
    if not force and not _is_trading_time():
        now_str = datetime.now(tz=_CN_TZ).strftime("%H:%M")
        snapshot["status"] = "skipped"
        snapshot["message"] = f"非交易时段（{now_str}）"
        return snapshot

    config = _load_app_config()
    params = _load_signal_params(config)
    ths_cookie: str | None = config.get("ths_cookie") or None

    # ── 1. 市场情绪 ────────────────────────────────────────────────────────
    sentiment = fetch_market_sentiment(ths_cookie)
    snapshot["market"] = {
        "limit_up": sentiment.limit_up,
        "limit_down": sentiment.limit_down,
        "danger_level": sentiment.danger_level,
    }

    # THS 明确报告市场未开盘（节假日 / 盘后）→ 跳过，避免基于昨日收盘价产生虚假信号
    if not force and not sentiment.market_open and sentiment.danger_level != "unknown":
        snapshot["status"] = "skipped"
        snapshot["message"] = f"THS 报告市场未开盘（{sentiment.danger_level}）"
        return snapshot

    buy_targets, source_lineage = _load_post_close_buy_targets()
    if sentiment.danger_level == "red":
        _write_signals(
            [],
            sentiment,
            sectors={},
            monitored={"buy_targets": 0, "universe": 0},
            source_run_id=str(source_lineage.get("source_run_id", "")),
            source_files=list(source_lineage.get("source_files", [])),
        )
        snapshot["status"] = "skipped"
        snapshot["message"] = "市场高压线（跌停 >= 80）"
        return snapshot

    # ── 2. 读取盘后买入信号 + 板块概览 ────────────────────────────────────────
    # buy_targets/source_lineage 已在 red 分支前读取，避免重复 IO
    try:
        sectors = fetch_market_sectors_top_n(5)
    except Exception:
        logger.exception("板块概览获取失败，降级为空")
        sectors = {}
    snapshot["market_sectors"] = sectors

    buy_codes = {str(s.get("code", "")).strip() for s in buy_targets if s.get("code")}
    pullback_state_map = _load_pullback_state()
    for stale_code in list(pullback_state_map):
        if stale_code not in buy_codes:
            pullback_state_map.pop(stale_code, None)

    # 监控池：仅盘后买入信号股
    universe = [
        {"code": str(item.get("code", "")).strip(), "name": item.get("name", str(item.get("code", "")))}
        for item in buy_targets
        if str(item.get("code", "")).strip()
    ]
    if not universe:
        _save_pullback_state({})
        _write_signals(
            [],
            sentiment,
            sectors=sectors,
            monitored={"buy_targets": 0, "universe": 0},
            source_run_id=str(source_lineage.get("source_run_id", "")),
            source_files=list(source_lineage.get("source_files", [])),
        )
        snapshot["status"] = "ok"
        snapshot["message"] = "买入信号为空"
        return snapshot

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
    with ThreadPoolExecutor(max_workers=min(8, len(universe))) as pool:
        futures = [pool.submit(_fetch_kline_job, s) for s in universe]
        for fut in futures:
            try:
                code, name, bars, weekly_bars = fut.result()
                kline_map[code] = (name, bars, weekly_bars)
            except Exception as exc:
                logger.warning("K 线获取异常: %s", exc)

    # ── 4. 批量获取腾讯实时行情 ───────────────────────────────────────────
    codes = list(kline_map.keys())
    realtime_map = _fetch_realtime(codes)

    # ── 5. 计算信号 ────────────────────────────────────────────────────────
    signals: list[StockSignal] = []
    for stock in buy_targets:
        code = str(stock.get("code", "")).strip()
        if not code:
            continue
        entry = kline_map.get(code)
        if entry is None:
            continue
        name, bars, weekly_bars = entry
        rt = realtime_map.get(code)
        if rt is None:
            logger.debug("实时行情缺失: %s", code)
            continue
        prev_state = pullback_state_map.get(code)
        sig, next_state = _analyze_signal(
            code, name, bars, weekly_bars, rt, sentiment, params, prev_state
        )
        if next_state is None:
            pullback_state_map.pop(code, None)
        else:
            pullback_state_map[code] = next_state
        if sig is not None:
            signals.append(sig)

    signals.sort(key=lambda s: -s.score)

    # ── 6. 写文件 ──────────────────────────────────────────────────────────
    _save_pullback_state(pullback_state_map)
    _write_signals(
        signals,
        sentiment,
        pullback_states=pullback_state_map,
        sectors=sectors,
        monitored={
            "buy_targets": len(buy_targets),
            "universe": len(universe),
        },
        source_run_id=str(source_lineage.get("source_run_id", "")),
        source_files=list(source_lineage.get("source_files", [])),
    )
    snapshot["signals"] = [asdict(s) for s in signals]
    snapshot["monitored"] = {
        "buy_targets": len(buy_targets),
        "universe": len(universe),
    }
    return snapshot


def main() -> None:
    """CLI 入口：手动启动持续监控，默认循环扫描并渲染终端面板。"""
    parser = argparse.ArgumentParser(description="A股监控终端（实时渲染）")
    parser.add_argument("--verbose", action="store_true", help="详细日志输出")
    parser.add_argument("--force", action="store_true", help="忽略交易时间限制（调试用）")
    parser.add_argument("--once", action="store_true", help="仅执行一次扫描后退出")
    parser.add_argument("--interval", type=int, default=20, help="循环模式下扫描间隔（秒）")
    parser.add_argument("--no-clear", action="store_true", help="不清屏，连续追加输出")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if args.once:
        snapshot = scan_once(force=args.force)
        _render_tui(snapshot, clear_screen=not args.no_clear)
        return

    try:
        while True:
            snapshot = scan_once(force=args.force)
            _render_tui(snapshot, clear_screen=not args.no_clear)
            time.sleep(max(3, args.interval))
    except KeyboardInterrupt:
        sys.stdout.write("\n已退出监控。\n")


if __name__ == "__main__":
    main()
