#!/usr/bin/env python3
"""Deprecated entrypoint for the old opencode-based analysis pipeline."""

import argparse
import sys


def _deprecated_message() -> str:
    return (
        "run_analysis.py 已废弃，不再通过 opencode 子代理执行复盘/选股/交易计划。\n"
        "请改用 ashare-assistant 的 SKILL 工作流，由 Openclaw 直接完成三个核心功能：\n"
        "1) 复盘（输出 market_review.md）\n"
        "2) 选股（输出 analysis/candidates.json）\n"
        "3) 交易计划（输出 trading_plan.md）"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deprecated: use SKILL.md workflow directly in Openclaw."
    )
    parser.add_argument("--data-dir", help="兼容旧参数，仅用于提示信息。")
    parser.add_argument(
        "--tasks",
        nargs="+",
        help="兼容旧参数，仅用于提示信息。",
    )
    parser.parse_args()
    print(f"[analysis] {_deprecated_message()}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
