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
from ashare_data.core.http_client import http_bytes, http_text
from ashare_data.core.watchlist import load as load_watchlist
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
    em_bars = _try_em_kline(code, days)
    if em_bars:
        return em_bars
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
    em_bars: list[_KlineBar],
    rt: _RealtimeQuote,
    sentiment: MarketSentiment,
) -> StockSignal | None:
    """综合 MA 位置、量价形态、市场情绪，计算买入信号得分。

    评分规则:
        当前价 < MA20                   → 直接排除（趋势破坏）
        当前价在 MA20–MA10 之间          → +20（回调到支撑区）
        当前价 >= MA10                   → +10（趋势完好）
        今日量 < 0.7×20日均量           → +20（缩量，抛压减轻）
        跌幅 -2% ~ -5%                  → +15（适度下跌）
        下影线 / 实体 > 0.5             → +15（有抵抗，买盘在撑）
        跌幅 < -2% 且量 > 1.5×均量     → -20（放量下跌，出货信号）
        跌幅 < -8%                      → -15（恐慌未止）
        星级 >= 4                       → +10（趋势评分强）
        黄色市场                        → 门槛提高 15 分

    Returns:
        StockSignal 或 None（不满足最低门槛时）。
    """
    today_str = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d")
    # 只用已完成交易日的历史 K 线，排除今日可能的半日数据
    hist = [b for b in em_bars if b.date < today_str]
    if len(hist) < 20:
        logger.debug("历史数据不足: %s (%d 条历史 K 线)", code, len(hist))
        return None

    closes = [b.close for b in hist]
    volumes = [b.volume for b in hist]

    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else (
        sum(volumes) / len(volumes) if volumes else 0.0
    )
    star = _compute_star(closes)

    current = rt.current
    change_pct = rt.change_pct
    today_vol = rt.volume_lot

    if current <= 0 or ma10 <= 0 or ma20 <= 0:
        return None

    # 硬排除：价格跌破 MA20（趋势破坏）
    if current < ma20:
        return None

    score = 0
    reasons: list[str] = []

    # ─ 价格位置
    if ma20 <= current < ma10:
        score += 20
        reasons.append("回调至MA10附近")
    else:
        # current >= ma10
        score += 10
        reasons.append("价格在MA10之上")

    # ─ 成交量对比
    if avg_vol_20 > 0:
        vol_ratio = today_vol / avg_vol_20
        if vol_ratio < 0.7:
            score += 20
            reasons.append("缩量")
        elif vol_ratio > 1.5 and change_pct < -2.0:
            score -= 20
            reasons.append("放量下跌")

    # ─ 涨跌幅
    if -5.0 <= change_pct <= -2.0:
        score += 15
        reasons.append(f"适度下跌({change_pct:.1f}%)")
    elif change_pct < -8.0:
        score -= 15
        reasons.append("跌幅过大")

    # ─ 下影线（买盘有抵抗）
    open_p, high, low = rt.open, rt.high, rt.low
    if open_p > 0 and low > 0 and high > 0:
        body = abs(current - open_p)
        lower_shadow = min(open_p, current) - low
        if body > 0 and lower_shadow / body > 0.5:
            score += 15
            reasons.append("下影线有支撑")

    # ─ 趋势星级加分
    if star >= 4:
        score += 10

    # ─ 黄色市场提高门槛
    threshold_bonus = 15 if sentiment.danger_level == "yellow" else 0
    threshold_buy = 35 + threshold_bonus
    threshold_watch = 15 + threshold_bonus

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
        ma10=round(ma10, 3),
        ma20=round(ma20, 3),
        star=star,
        score=score,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _write_signals(
    signals: list[StockSignal],
    watched: list[StockSignal],
    sentiment: MarketSentiment,
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
    }
    with open(_SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(
        "信号文件已写入: %s（buy_dip=%d, watch=%d）",
        _SIGNALS_FILE,
        len(signals),
        len(watched),
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

    # ── 3. 并发拉取东方财富日 K ────────────────────────────────────────────
    def _fetch_kline_job(
        stock: dict[str, Any],
    ) -> tuple[str, str, list[_KlineBar]]:
        code = stock["code"]
        name = stock.get("name", code)
        bars = _fetch_em_kline(code, days=26)
        return code, name, bars

    kline_map: dict[str, tuple[str, list[_KlineBar]]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(active))) as pool:
        futures = [pool.submit(_fetch_kline_job, s) for s in active]
        for fut in futures:
            try:
                code, name, bars = fut.result()
                kline_map[code] = (name, bars)
            except Exception as exc:
                logger.warning("K 线获取异常: %s", exc)

    # ── 4. 批量获取腾讯实时行情 ───────────────────────────────────────────
    codes = list(kline_map.keys())
    realtime_map = _fetch_realtime(codes)
    logger.info("实时行情获取: %d/%d 只", len(realtime_map), len(codes))

    # ── 5. 计算信号 ────────────────────────────────────────────────────────
    buy_signals: list[StockSignal] = []
    watch_signals: list[StockSignal] = []

    for code, (name, bars) in kline_map.items():
        rt = realtime_map.get(code)
        if rt is None:
            logger.debug("实时行情缺失: %s", code)
            continue
        sig = _analyze_signal(code, name, bars, rt, sentiment)
        if sig is None:
            continue
        if sig.signal == "buy_dip":
            buy_signals.append(sig)
        else:
            watch_signals.append(sig)

    buy_signals.sort(key=lambda s: -s.score)
    watch_signals.sort(key=lambda s: -s.score)

    # ── 6. 写文件 ──────────────────────────────────────────────────────────
    _write_signals(buy_signals, watch_signals, sentiment)
    logger.info("扫描完成: buy_dip=%d, watch=%d", len(buy_signals), len(watch_signals))


if __name__ == "__main__":
    main()
