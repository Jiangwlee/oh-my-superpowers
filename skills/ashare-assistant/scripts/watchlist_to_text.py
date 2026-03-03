#!/usr/bin/env python3
"""将 watchlist_signals.json 转换为人类友好的终端输出。"""

import json
from pathlib import Path

HOME = Path.home()
SIGNALS_FILE = HOME / ".ashare-assistant/signals/watchlist_signals.json"


def format_signal(stock: dict) -> str:
    """格式化单个状态机信号。"""
    code = stock["code"]
    name = stock["name"]
    state = stock["state"]
    reason = stock["reason"]
    price = f"{stock['price']:.2f}"
    change = f"{stock['change']:+.2f}%"
    ma5w = f"{stock['ma5w']:.2f}"
    vr20d = f"{stock['vr20d']:.2f}"
    dev20w = f"{stock['dev20w'] * 100:+.1f}%"
    score = stock["score"]
    action = stock["action_next_day"]

    return (
        f"  {code} {name:<8} | {state:<6} | "
        f"价格：{price:>7} ({change:>7}) | MA5W: {ma5w:>7} | VR20D: {vr20d:>5} | "
        f"DEV20W: {dev20w:>7} | 动作: {action:<18} | {score:>3}分\n"
        f"    理由: {reason}"
    )


def format_exit(stock: dict) -> str:
    """格式化出场信号。"""
    code = stock["code"]
    name = stock["name"]
    state = stock["state"]
    price = f"{stock['price']:.2f}"
    action = stock["action_next_day"]
    reason = stock["reason"]
    return (
        f"  {code} {name:<8} | {state:<6} | 价格: {price:>7} | 动作: {action}\n"
        f"    理由: {reason}"
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
    print("状态信号")
    print("-" * 80)

    signals = data["signals"]
    if not signals:
        print("  无信号")
        sorted_signals = []
    else:
        sorted_signals = sorted(signals, key=lambda s: s["score"], reverse=True)

    for stock in sorted_signals:
        print(format_signal(stock))
        print()

    exits = data.get("exits", [])
    print("-" * 80)
    print("出场信号")
    print("-" * 80)
    if not exits:
        print("  无出场信号")
    else:
        for item in exits:
            print(format_exit(item))
            print()

    state_count: dict[str, int] = {}
    for item in signals:
        state = str(item.get("state", "UNKNOWN"))
        state_count[state] = state_count.get(state, 0) + 1

    print()
    print("=" * 80)
    print("共 {} 个状态信号，{} 个出场信号".format(len(signals), len(exits)))
    print("状态分布: {}".format(state_count))
    print("=" * 80)


if __name__ == "__main__":
    print_signals()
