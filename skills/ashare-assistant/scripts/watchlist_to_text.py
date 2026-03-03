#!/usr/bin/env python3
"""将 watchlist_signals.json 转换为人类友好的终端输出。"""

import json
from pathlib import Path

HOME = Path.home()
SIGNALS_FILE = HOME / ".ashare-assistant/signals/watchlist_signals.json"


def format_signal(stock: dict) -> str:
    """格式化单个股票信号。"""
    code = stock["code"]
    name = stock["name"]
    signal = stock["signal"]
    reason = stock["reason"]
    price = f"{stock['price']:.2f}"
    change = f"{stock['change']:+.2f}%"
    ma10 = f"{stock['ma10']:.2f}"
    ma20 = f"{stock['ma20']:.2f}"
    star = "★" * stock["star"]
    score = stock["score"]

    return (
        f"  {code} {name:<8} | {signal:<8} | "
        f"价格：{price:>7} ({change:>6}) | MA10: {ma10:>7} | MA20: {ma20:>7} | "
        f"{star} ({score}分)"
    )


def print_signals() -> None:
    """读取并打印信号。"""
    data = json.loads(SIGNALS_FILE.read_text())

    scanned_at = data["scanned_at"]
    market = data["market"]

    print("=" * 80)
    print(f"信号扫描时间：{scanned_at}")
    print("=" * 80)
    print()
    print("市场概览")
    print("  涨停：   {:>5} 股".format(market["limit_up"]))
    print("  跌停：   {:>5} 股".format(market["limit_down"]))
    print("  风险：   {:>6}".format(market["danger_level"]))
    print()
    print("-" * 80)
    print("信号列表")
    print("-" * 80)

    signals = data["signals"]
    if not signals:
        print("  无信号")
        return

    # 按分数排序
    sorted_signals = sorted(signals, key=lambda s: s["score"], reverse=True)

    for stock in sorted_signals:
        print(format_signal(stock))

    print()
    print("=" * 80)
    print("共 {} 个信号".format(len(signals)))
    print("=" * 80)


if __name__ == "__main__":
    print_signals()
