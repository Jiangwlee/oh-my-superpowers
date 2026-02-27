#!/usr/bin/env python3
"""持仓洞察模块（holding_insight）。
对每只持仓股进行规则引擎决策，输出 加仓/持有/卖出 建议，
附带具体价格和数量（数量为100的整数倍）。
决策规则链（瀑布式，命中即停）：
  Level 0: 账户模式强制规则
  Level 1: 硬止损
  Level 2: 止盈
  Level 3: 技术面弱化
  Level 4: 加仓机会
  Level 5: 默认持有
数据来源：
  - JVQuant: 仅用于获取持仓/资金（付费，受 call guard 保护）
  - JRJ K线: 免费，用于技术分析
  - 资金面: 免费，仅作辅助参考
"""

from __future__ import annotations
import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_data.fetchers.broker_account import fetch_broker_account, load_history
from scripts.core import shared as shared_core
from ashare_data.fetchers.trend_scanner import (
    TrendResult,
    analyze_trend,
    apply_scoring,
    fetch_jrj_daily_kline,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 工具函数（部分与 trade_review.py 共用逻辑，为保持模块独立性此处复制）
# ---------------------------------------------------------------------------
def _now_cn_iso() -> str:
    return shared_core.now_cn_iso()


def _today_cn() -> str:
    return shared_core.today_cn()


def _safe_float(value: Any, default: float = 0.0) -> float:
    return shared_core.safe_float(value, default)


def _safe_int(value: Any, default: int = 0) -> int:
    return shared_core.safe_int(value, default)


def _norm_code(value: Any) -> str:
    return shared_core.norm_code(value)


def _extract_pct_limit(text: str, fallback: float) -> float:
    return shared_core.extract_pct_limit(text, fallback)


def _parse_range_to_pct(text: str) -> tuple[float, float] | None:
    return shared_core.parse_range_to_pct(text)


def _load_strategy(yaml_path: str) -> dict[str, Any]:
    return shared_core.load_strategy(yaml_path, logger=logger)


def _determine_account_mode(total: float, hold_earn: float) -> str:
    return shared_core.determine_account_mode(total, hold_earn)


def _position_market_value(pos: dict[str, Any]) -> float:
    return shared_core.position_market_value(pos)


def _holding_days_from_history(code: str, history: dict[str, Any]) -> int:
    return shared_core.holding_days_from_history(code, history)


def _below_ma20_streak(closes: list[float]) -> int:
    """从K线收盘价序列计算连续低于MA20的天数（从最新一天往回数）。"""
    if len(closes) < 20:
        return 0
    streak = 0
    for i in range(len(closes) - 1, 19, -1):
        ma20 = sum(closes[i - 19 : i + 1]) / 20.0
        if closes[i] < ma20:
            streak += 1
        else:
            break
    return streak


def _ma5_deviation(closes: list[float]) -> float:
    """计算最新收盘价相对MA5的偏离比例。"""
    if len(closes) < 5:
        return 0.0
    ma5 = sum(closes[-5:]) / 5.0
    if ma5 <= 0:
        return 0.0
    return (closes[-1] - ma5) / ma5


def _enrich_hold_list_prices(hold_list: list[dict[str, Any]]) -> None:
    """为缺少现价的持仓补充JRJ日K线最新收盘价（原地修改）。"""
    shared_core.enrich_hold_list_prices(
        hold_list,
        fetch_daily_kline=fetch_jrj_daily_kline,
        logger=logger,
    )


# ---------------------------------------------------------------------------
# HoldingDecision 数据类
# ---------------------------------------------------------------------------
@dataclass
class HoldingDecision:
    """单只持仓的决策结果。"""

    code: str = ""
    name: str = ""
    action: str = "hold"  # "sell" | "hold" | "add"
    urgency: str = "next_session"  # "immediate" | "today" | "next_session"
    target_price: float | None = None  # 建议价格
    target_qty: int | None = None  # 建议数量（100的整数倍）
    price_type: str = "limit"  # "limit" | "market"
    sell_pct: float | None = None  # 卖出比例（如 0.5 = 50%）
    reasons: list[str] = field(default_factory=list)
    risk_level: str = "low"  # "high" | "medium" | "low"
    rule_level: int = 5  # 命中的规则层级 (0-5)
    # 技术面快照
    trend_score: float = 0.0
    star_rating: int = 1
    trade_signal: str = "观察"
    emotion_label: str = "情绪不佳"
    is_uptrend: bool = False
    defense_safe_ratio: float = 0.0
    emotion_level: int = 1
    # 持仓快照
    position_pct: float = 0.0  # 当前仓位占比(%)
    pnl_pct: float = 0.0  # 当前盈亏比例(%)
    hold_vol: int = 0
    usable_vol: int = 0
    last_price: float = 0.0
    market_value: float = 0.0
    holding_days: int = 0
    # MA 数据
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma5_deviation_pct: float = 0.0
    below_ma20_days: int = 0
    # 资金面（辅助）
    net_inflow: float | None = None  # 主力净流入（亿元）

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 趋势分析（批量，并发获取K线）
# ---------------------------------------------------------------------------
def _analyze_holdings_trend(
    hold_list: list[dict[str, Any]],
) -> dict[str, tuple[TrendResult, list[dict[str, Any]]]]:
    """为每只持仓运行 analyze_trend，返回 {code: (TrendResult, kline)}。"""
    result_map: dict[str, tuple[TrendResult, list[dict[str, Any]]]] = {}
    items = []
    for pos in hold_list:
        if not isinstance(pos, dict):
            continue
        code = _norm_code(pos.get("code"))
        name = str(pos.get("name") or "")
        if not code:
            continue
        sc = f"SH{code}" if code.startswith("6") else f"SZ{code}"
        items.append({"code": code, "name": name, "sc": sc})
    if not items:
        return result_map

    def _run(item: dict) -> tuple[str, TrendResult, list[dict[str, Any]]]:
        tr, kline = analyze_trend(
            code=item["code"],
            sc=item["sc"],
            name=item["name"],
            rank=0,
            source="holding_insight",
        )
        return item["code"], tr, kline

    with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
        futs = {pool.submit(_run, item): item["code"] for item in items}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                c, tr, kline = fut.result()
                result_map[c] = (tr, kline)
            except Exception:
                logger.exception("趋势分析失败: %s", code)
    # 批量评分（需要所有结果一起计算分位数）
    all_results = [v[0] for v in result_map.values()]
    if all_results:
        apply_scoring(all_results)
    return result_map


# ---------------------------------------------------------------------------
# 资金面查询（零成本）
# ---------------------------------------------------------------------------
def _fetch_funding_info(codes: list[str]) -> dict[str, float]:
    """尝试获取持仓股的主力净流入，返回 {code: net_inflow_亿}。失败返回空。"""
    try:
        from ashare_data.fetchers.funding import fetch_funding_for_codes

        results = fetch_funding_for_codes(codes)
        return {r["code"]: r.get("net_inflow", 0.0) for r in results}
    except Exception:
        logger.debug("资金面查询不可用，跳过")
        return {}


# ---------------------------------------------------------------------------
# 数量计算
# ---------------------------------------------------------------------------
def _round_down_100(qty: float) -> int:
    """向下取整到100的整数倍。"""
    return int(qty // 100) * 100


def _calc_sell_qty(usable_vol: int, sell_pct: float) -> int:
    """计算卖出数量。
    Args:
        usable_vol: 可用数量（T+1 当日买入不可卖）。
        sell_pct: 卖出比例，1.0 = 全部。
    Returns:
        卖出数量（100的整数倍），最少100股，不足则返回 usable_vol。
    """
    if usable_vol <= 0:
        return 0
    if sell_pct >= 1.0:
        return usable_vol
    raw = usable_vol * sell_pct
    qty = _round_down_100(raw)
    if qty < 100:
        qty = min(100, usable_vol)
    return min(qty, usable_vol)


def _calc_add_qty(
    *,
    last_price: float,
    total_assets: float,
    usable_cash: float,
    current_position_pct: float,
    single_limit_pct: float,
    total_position_pct: float,
    regime_upper_pct: float,
) -> int:
    """计算加仓数量。
    Args:
        last_price: 当前价格。
        total_assets: 账户总资产。
        usable_cash: 可用资金。
        current_position_pct: 当前该股仓位占比(0-100)。
        single_limit_pct: 单股仓位上限(0-100)。
        total_position_pct: 当前总仓位占比(0-100)。
        regime_upper_pct: 当前市场状态允许的最大总仓位(0-100)。
    Returns:
        加仓数量（100的整数倍），不足100则返回0。
    """
    if last_price <= 0 or total_assets <= 0:
        return 0
    # 仓位空间（取单股限制和总仓位限制的较小值）
    single_room_pct = max(0, single_limit_pct - current_position_pct)
    total_room_pct = max(0, regime_upper_pct - total_position_pct)
    room_pct = min(single_room_pct, total_room_pct)
    if room_pct <= 0:
        return 0
    room_value = total_assets * room_pct / 100.0
    # 资金约束：留5%余量
    cash_limit = usable_cash * 0.95
    max_value = min(room_value, cash_limit)
    if max_value < last_price * 100:
        return 0
    qty = _round_down_100(max_value / last_price)
    return qty


def _calc_sell_price(last_price: float, urgency: str) -> tuple[float, str]:
    """计算卖出挂单价格。"""
    if urgency == "immediate":
        return round(last_price * 0.97, 2), "market"  # 市价模拟：跌停价附近
    if urgency == "today":
        return round(last_price * 0.998, 2), "limit"
    return round(last_price * 0.995, 2), "limit"


def _calc_add_price(last_price: float, ma10: float) -> float:
    """计算加仓挂单价格：取 MA10 和现价折扣的较低者。"""
    ma10_price = ma10 if ma10 > 0 else last_price
    discount_price = last_price * 0.99
    return round(min(ma10_price, discount_price), 2)


# ---------------------------------------------------------------------------
# 单股决策引擎
# ---------------------------------------------------------------------------
def _decide_single(
    *,
    pos: dict[str, Any],
    trend: TrendResult | None,
    kline: list[dict[str, Any]],
    account_mode: str,
    total_assets: float,
    usable_cash: float,
    total_position_pct: float,
    single_limit_pct: float,
    regime_upper_pct: float,
    history: dict[str, Any],
    funding_map: dict[str, float],
) -> HoldingDecision:
    """对单只持仓执行瀑布式规则链决策。"""
    code = _norm_code(pos.get("code"))
    name = str(pos.get("name") or "")
    hold_vol = _safe_int(pos.get("hold_vol") or pos.get("volume") or pos.get("qty"))
    usable_vol = _safe_int(pos.get("usable_vol") or hold_vol)
    last_price = _safe_float(
        pos.get("last_price") or pos.get("current_price") or pos.get("price")
    )
    market_value = _position_market_value(pos)
    position_pct = (market_value / total_assets * 100.0) if total_assets > 0 else 0.0
    holding_days = _holding_days_from_history(code, history)
    # 盈亏计算
    hold_earn = _safe_float(pos.get("hold_earn"))
    cost_price = _safe_float(pos.get("cost_price"))
    if cost_price > 0 and last_price > 0:
        pnl_pct = (last_price - cost_price) / cost_price * 100.0
    elif market_value > 0 and hold_earn != 0:
        cost_value = market_value - hold_earn
        pnl_pct = (hold_earn / cost_value * 100.0) if cost_value > 0 else 0.0
    else:
        pnl_pct = 0.0
    # K线计算 MA
    closes = [
        _safe_float(b.get("close")) for b in kline if _safe_float(b.get("close")) > 0
    ]
    ma5 = sum(closes[-5:]) / 5.0 if len(closes) >= 5 else 0.0
    ma10 = sum(closes[-10:]) / 10.0 if len(closes) >= 10 else 0.0
    ma20 = sum(closes[-20:]) / 20.0 if len(closes) >= 20 else 0.0
    ma5_dev = _ma5_deviation(closes)
    below_ma20 = _below_ma20_streak(closes)
    # 趋势信息
    is_uptrend = trend.is_uptrend if trend else False
    star_rating = trend.star_rating if trend else 1
    trade_signal = trend.trade_signal if trend else "观察"
    emotion_label = trend.emotion_label if trend else "情绪不佳"
    emotion_level = trend.emotion_level if trend else 1
    trend_score = trend.score_total_100 if trend else 0.0
    defense_safe_ratio = trend.defense_safe_ratio if trend else 0.0
    # 资金面
    net_inflow = funding_map.get(code)
    # 构建基础 decision
    d = HoldingDecision(
        code=code,
        name=name,
        hold_vol=hold_vol,
        usable_vol=usable_vol,
        last_price=last_price,
        market_value=round(market_value, 2),
        position_pct=round(position_pct, 2),
        pnl_pct=round(pnl_pct, 2),
        holding_days=holding_days,
        trend_score=round(trend_score, 2),
        star_rating=star_rating,
        trade_signal=trade_signal,
        emotion_label=emotion_label,
        emotion_level=emotion_level,
        is_uptrend=is_uptrend,
        defense_safe_ratio=round(defense_safe_ratio, 4),
        ma5=round(ma5, 4),
        ma10=round(ma10, 4),
        ma20=round(ma20, 4),
        ma5_deviation_pct=round(ma5_dev * 100, 2),
        below_ma20_days=below_ma20,
        net_inflow=net_inflow,
    )
    # ===================================================================
    # 瀑布式规则链
    # ===================================================================
    # --- Level 0: 账户模式强制规则 ---
    if account_mode == "critical":
        if not is_uptrend:
            d.action = "sell"
            d.urgency = "today"
            d.sell_pct = 1.0
            d.risk_level = "high"
            d.rule_level = 0
            d.reasons = ["危急模式(亏损>=30%), 趋势已破, 逐步清仓"]
            qty = _calc_sell_qty(usable_vol, 1.0)
            price, ptype = _calc_sell_price(last_price, "today")
            d.target_qty = qty
            d.target_price = price
            d.price_type = ptype
            return d
        else:
            # critical 但趋势完好 → hold + 高风险警告，不加仓
            d.action = "hold"
            d.urgency = "today"
            d.risk_level = "high"
            d.rule_level = 0
            d.reasons = ["危急模式, 趋势暂完好可暂持, 密切观察, 禁止加仓"]
            return d
    if account_mode == "defensive":
        # defensive 不会触发卖出，只是标记禁止加仓（后续 Level 4 会检查）
        pass
    # --- Level 1: 硬止损 ---
    if below_ma20 >= 3:
        d.action = "sell"
        d.urgency = "immediate"
        d.sell_pct = 1.0
        d.risk_level = "high"
        d.rule_level = 1
        d.reasons = [f"MA20止损: 连续{below_ma20}日跌破MA20未收回(>=3日)"]
        qty = _calc_sell_qty(usable_vol, 1.0)
        price, ptype = _calc_sell_price(last_price, "immediate")
        d.target_qty = qty
        d.target_price = price
        d.price_type = ptype
        return d
    if pnl_pct <= -15.0 and not is_uptrend:
        d.action = "sell"
        d.urgency = "today"
        d.sell_pct = 1.0
        d.risk_level = "high"
        d.rule_level = 1
        d.reasons = [f"亏损{pnl_pct:.1f}%且趋势已破(is_uptrend=False), 执行止损"]
        qty = _calc_sell_qty(usable_vol, 1.0)
        price, ptype = _calc_sell_price(last_price, "today")
        d.target_qty = qty
        d.target_price = price
        d.price_type = ptype
        return d
    if pnl_pct <= -15.0 and is_uptrend:
        # 亏损大但趋势完好 → hold + 高风险警告
        d.action = "hold"
        d.risk_level = "high"
        d.rule_level = 1
        d.reasons = [f"亏损{pnl_pct:.1f}%但趋势完好, 暂持观察, 注意风险"]
        return d
    # --- Level 2: 止盈 ---
    if ma5_dev >= 0.20:
        d.action = "sell"
        d.urgency = "immediate"
        d.sell_pct = 0.5
        d.risk_level = "medium"
        d.rule_level = 2
        d.reasons = [f"MA5偏离{ma5_dev * 100:.1f}%(>=20%), 减仓50%锁利"]
        qty = _calc_sell_qty(usable_vol, 0.5)
        price, ptype = _calc_sell_price(last_price, "immediate")
        d.target_qty = qty
        d.target_price = price
        d.price_type = ptype
        return d
    if ma5_dev >= 0.15:
        d.action = "sell"
        d.urgency = "today"
        d.sell_pct = 0.3
        d.risk_level = "medium"
        d.rule_level = 2
        d.reasons = [f"MA5偏离{ma5_dev * 100:.1f}%(>=15%), 减仓30%锁利"]
        qty = _calc_sell_qty(usable_vol, 0.3)
        price, ptype = _calc_sell_price(last_price, "today")
        d.target_qty = qty
        d.target_price = price
        d.price_type = ptype
        return d
    if star_rating <= 2 and not is_uptrend:
        d.action = "sell"
        d.urgency = "today"
        d.sell_pct = 1.0
        d.risk_level = "medium"
        d.rule_level = 2
        d.reasons = [f"评分{star_rating}星(<=2)且趋势已破, 清仓"]
        qty = _calc_sell_qty(usable_vol, 1.0)
        price, ptype = _calc_sell_price(last_price, "today")
        d.target_qty = qty
        d.target_price = price
        d.price_type = ptype
        return d
    # --- Level 3: 技术面弱化 ---
    if not is_uptrend and holding_days > 5 and star_rating <= 2:
        d.action = "sell"
        d.urgency = "next_session"
        d.sell_pct = 1.0
        d.risk_level = "medium"
        d.rule_level = 3
        d.reasons = [f"趋势破坏+持仓{holding_days}日+评分{star_rating}星, 建议清仓"]
        qty = _calc_sell_qty(usable_vol, 1.0)
        price, ptype = _calc_sell_price(last_price, "next_session")
        d.target_qty = qty
        d.target_price = price
        d.price_type = ptype
        return d
    if not is_uptrend and holding_days > 5 and star_rating >= 3:
        d.action = "hold"
        d.risk_level = "medium"
        d.rule_level = 3
        d.reasons = [f"趋势破坏但评分{star_rating}星尚可, 观察是否回暖, 暂持"]
        return d
    if below_ma20 >= 1:
        d.action = "hold"
        d.risk_level = "medium"
        d.rule_level = 3
        d.reasons = [f"逼近MA20止损线(跌破{below_ma20}日), 密切观察, 暂持"]
        return d
    # --- Level 4: 加仓机会 ---
    # 所有前提条件检查
    can_add = True
    add_block_reasons: list[str] = []
    if account_mode in ("defensive", "critical"):
        can_add = False
        add_block_reasons.append(f"账户模式={account_mode}, 禁止加仓")
    if position_pct >= single_limit_pct:
        can_add = False
        add_block_reasons.append(
            f"单股仓位{position_pct:.1f}%已达上限{single_limit_pct:.0f}%"
        )
    if total_position_pct >= regime_upper_pct:
        can_add = False
        add_block_reasons.append(
            f"总仓位{total_position_pct:.1f}%已达上限{regime_upper_pct:.0f}%"
        )
    if pnl_pct < 0:
        can_add = False
        add_block_reasons.append(f"当前亏损{pnl_pct:.1f}%, 不对亏损仓加仓")
    if pnl_pct >= 20.0:
        can_add = False
        add_block_reasons.append(f"浮盈{pnl_pct:.1f}%(>=20%), 锁利优先不加仓")
    if defense_safe_ratio < 0.7:
        can_add = False
        add_block_reasons.append(
            f"防守能力不足(safe_ratio={defense_safe_ratio:.2f}<0.7)"
        )
    if emotion_level < 3:
        can_add = False
        add_block_reasons.append(f"情绪偏弱({emotion_label}), 不宜加仓")
    if can_add and is_uptrend and star_rating >= 4:
        # 判断是否在MA10附近回调
        near_ma10 = (
            ma10 > 0 and last_price > 0 and abs(last_price - ma10) / ma10 <= 0.01
        )
        add_price = _calc_add_price(last_price, ma10)
        add_qty = _calc_add_qty(
            last_price=add_price,
            total_assets=total_assets,
            usable_cash=usable_cash,
            current_position_pct=position_pct,
            single_limit_pct=single_limit_pct,
            total_position_pct=total_position_pct,
            regime_upper_pct=regime_upper_pct,
        )
        if add_qty >= 100:
            d.action = "add"
            d.urgency = "next_session"
            d.risk_level = "low"
            d.rule_level = 4
            d.target_price = add_price
            d.target_qty = add_qty
            d.price_type = "limit"
            if near_ma10:
                d.reasons = [f"回调至MA10附近(±1%), {star_rating}星趋势完好, 建议加仓"]
            else:
                d.reasons = [f"{star_rating}星趋势完好, 可小量加仓"]
            # 资金面辅助信息
            if net_inflow is not None:
                flow_desc = (
                    f"主力净流入{net_inflow:.2f}亿"
                    if net_inflow > 0
                    else f"主力净流出{abs(net_inflow):.2f}亿"
                )
                d.reasons.append(f"(参考) {flow_desc}")
            return d
    # --- Level 5: 默认持有 ---
    d.action = "hold"
    d.risk_level = "low"
    d.rule_level = 5
    reasons = ["技术面正常, 继续持有"]
    if add_block_reasons:
        reasons.append(f"加仓受限: {'; '.join(add_block_reasons)}")
    if net_inflow is not None:
        flow_desc = (
            f"主力净流入{net_inflow:.2f}亿"
            if net_inflow > 0
            else f"主力净流出{abs(net_inflow):.2f}亿"
        )
        reasons.append(f"(参考) {flow_desc}")
    d.reasons = reasons
    return d


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def analyze_holdings(
    broker_data: dict[str, Any] | None = None,
    strategy_path: str = "strategy/active.yaml",
    market_regime: str = "neutral",
    output_path: str | None = None,
) -> dict[str, Any]:
    """分析所有持仓并生成操作建议。
    Args:
        broker_data: 券商账户数据，None 则自动获取。
        strategy_path: 策略文件路径。
        market_regime: 市场状态 ("strong" / "neutral" / "weak")。
        output_path: 输出 JSON 路径，None 则不写文件。
    Returns:
        完整分析结果字典。
    """
    logger.info("=== 持仓洞察分析开始 ===")
    # 1. 获取账户数据
    if broker_data is None:
        try:
            broker_data = fetch_broker_account()
        except Exception:
            logger.exception("获取券商数据失败")
            return {"error": "获取券商数据失败", "decisions": []}
    total_assets = _safe_float(broker_data.get("total"))
    usable_cash = _safe_float(broker_data.get("usable"))
    hold_earn = _safe_float(broker_data.get("hold_earn"))
    hold_list = broker_data.get("hold_list", [])
    if not isinstance(hold_list, list):
        hold_list = []
    # 过滤已清仓记录 (当日卖出后 hold_vol=0 但 JVQuant 仍返回)
    hold_list = [
        p
        for p in hold_list
        if isinstance(p, dict)
        and _safe_int(p.get("hold_vol") or p.get("volume") or p.get("qty")) > 0
    ]
    if not hold_list:
        logger.info("无持仓，跳过分析")
        return {
            "review_date": _today_cn(),
            "generated_at": _now_cn_iso(),
            "account_snapshot": {
                "total_assets": total_assets,
                "usable_cash": usable_cash,
                "hold_earn": hold_earn,
                "position_count": 0,
            },
            "decisions": [],
            "summary": {"sell_count": 0, "hold_count": 0, "add_count": 0},
        }
    # 2. 补充持仓价格
    _enrich_hold_list_prices(hold_list)
    # 3. 加载策略 & 历史
    strategy = _load_strategy(strategy_path)
    history = load_history(days=30)
    # 4. 计算账户模式和仓位
    account_mode = _determine_account_mode(total_assets, hold_earn)
    total_position_pct = (
        ((total_assets - usable_cash) / total_assets * 100.0)
        if total_assets > 0
        else 0.0
    )
    # 解析策略限制
    trend_cfg = strategy.get("trend_stock", {})
    single_limit_pct = (
        _extract_pct_limit(
            str(trend_cfg.get("position", "") if isinstance(trend_cfg, dict) else ""),
            0.20,
        )
        * 100.0
    )  # 转为百分比
    market_pos = strategy.get("market_position", {})
    regime_str = str(
        market_pos.get(market_regime, "30-50%")
        if isinstance(market_pos, dict)
        else "30-50%"
    )
    regime_range = _parse_range_to_pct(regime_str)
    regime_upper_pct = regime_range[1] if regime_range else 50.0
    logger.info(
        "账户模式=%s, 总仓位=%.1f%%, 单股上限=%.0f%%, 市场上限=%.0f%%",
        account_mode,
        total_position_pct,
        single_limit_pct,
        regime_upper_pct,
    )
    # 5. 批量趋势分析
    trend_map = _analyze_holdings_trend(hold_list)
    # 6. 资金面查询
    codes = [_norm_code(p.get("code")) for p in hold_list if _norm_code(p.get("code"))]
    funding_map = _fetch_funding_info(codes)
    # 7. 逐股决策
    decisions: list[HoldingDecision] = []
    for pos in hold_list:
        if not isinstance(pos, dict):
            continue
        code = _norm_code(pos.get("code"))
        if not code:
            continue
        # 过滤已清仓记录 (当日卖出后 hold_vol=0 但 JVQuant 仍返回)
        if _safe_int(pos.get("hold_vol") or pos.get("volume") or pos.get("qty")) <= 0:
            continue
        trend_data = trend_map.get(code)
        trend_result = trend_data[0] if trend_data else None
        kline = trend_data[1] if trend_data else []
        decision = _decide_single(
            pos=pos,
            trend=trend_result,
            kline=kline,
            account_mode=account_mode,
            total_assets=total_assets,
            usable_cash=usable_cash,
            total_position_pct=total_position_pct,
            single_limit_pct=single_limit_pct,
            regime_upper_pct=regime_upper_pct,
            history=history,
            funding_map=funding_map,
        )
        decisions.append(decision)
    # 8. 汇总
    sell_count = sum(1 for d in decisions if d.action == "sell")
    hold_count = sum(1 for d in decisions if d.action == "hold")
    add_count = sum(1 for d in decisions if d.action == "add")
    # 按紧急程度排序：immediate > today > next_session
    urgency_order = {"immediate": 0, "today": 1, "next_session": 2}
    decisions.sort(
        key=lambda d: (
            0 if d.action == "sell" else (2 if d.action == "add" else 1),
            urgency_order.get(d.urgency, 9),
        )
    )
    result = {
        "review_date": _today_cn(),
        "generated_at": _now_cn_iso(),
        "account_snapshot": {
            "total_assets": round(total_assets, 2),
            "usable_cash": round(usable_cash, 2),
            "hold_earn": round(hold_earn, 2),
            "account_mode": account_mode,
            "total_position_pct": round(total_position_pct, 2),
            "market_regime": market_regime,
            "position_count": len(hold_list),
        },
        "decisions": [d.to_dict() for d in decisions],
        "summary": {
            "sell_count": sell_count,
            "hold_count": hold_count,
            "add_count": add_count,
            "high_risk_count": sum(1 for d in decisions if d.risk_level == "high"),
        },
    }
    # 9. 写出
    if output_path:
        try:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info("结果已写入: %s", output_path)
        except Exception:
            logger.exception("写入结果失败: %s", output_path)
    logger.info(
        "=== 持仓洞察完成: %d卖 / %d持 / %d加 ===",
        sell_count,
        hold_count,
        add_count,
    )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_summary_text(result: dict[str, Any]) -> str:
    """构建可读的文本摘要。"""
    lines: list[str] = []
    snap = result.get("account_snapshot", {})
    lines.append(f"持仓洞察 — {result.get('review_date', '')}")
    lines.append(
        f"账户模式: {snap.get('account_mode', '?')} | "
        f"总仓位: {snap.get('total_position_pct', 0):.1f}% | "
        f"市场: {snap.get('market_regime', '?')}"
    )
    lines.append("")
    summary = result.get("summary", {})
    lines.append(
        f"决策汇总: {summary.get('sell_count', 0)}卖 / "
        f"{summary.get('hold_count', 0)}持 / "
        f"{summary.get('add_count', 0)}加"
    )
    if summary.get("high_risk_count", 0) > 0:
        lines.append(f"  高风险: {summary['high_risk_count']}只")
    lines.append("")
    for d in result.get("decisions", []):
        action_zh = {"sell": "卖出", "hold": "持有", "add": "加仓"}.get(
            d.get("action", ""), "?"
        )
        urgency_zh = {
            "immediate": "立即",
            "today": "今日",
            "next_session": "下一交易日",
        }.get(d.get("urgency", ""), "")
        line = f"[{action_zh}] {d.get('name', '')}({d.get('code', '')})"
        if d.get("target_qty"):
            line += f" | {d['target_qty']}股 @ {d.get('target_price', '?')}"
        if urgency_zh:
            line += f" | {urgency_zh}"
        line += f" | {d.get('star_rating', '?')}星 {d.get('trend_score', 0):.0f}分"
        line += f" | 仓位{d.get('position_pct', 0):.1f}% 盈亏{d.get('pnl_pct', 0):.1f}%"
        lines.append(line)
        for reason in d.get("reasons", []):
            lines.append(f"  -> {reason}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="持仓洞察分析")
    parser.add_argument(
        "--strategy", default="strategy/active.yaml", help="策略文件路径"
    )
    parser.add_argument(
        "--regime",
        default="neutral",
        choices=["strong", "neutral", "weak"],
        help="市场状态",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出JSON路径（默认：~/.ashare-assistant/data/今日/analysis/holding_insight.json）",
    )
    parser.add_argument("--text", action="store_true", help="输出可读文本")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.output:
        output_path = args.output
    else:
        from ashare_data.core.config import data_dir_for_date

        output_path = str(data_dir_for_date() / "analysis" / "holding_insight.json")

    result = analyze_holdings(
        strategy_path=args.strategy,
        market_regime=args.regime,
        output_path=output_path,
    )
    if args.text:
        print(_build_summary_text(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
