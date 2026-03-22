"""Command-line entrypoint for backend task execution.

Purpose: Provide a unified CLI for running backend tasks without exposing write APIs.

Public API:
    main() -> None
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable

from app.tasks.build_market_review import run as run_build_market_review
from app.tasks.build_emotion_facts import run as run_build_emotion_facts
from app.tasks.build_theme_pool import run as run_build_theme_pool
from app.tasks.build_trend_pool import run as run_build_trend_pool
from app.tasks.collect_all import run as run_collect_all
from app.tasks.cleanup_ephemeral_data import run as run_cleanup_ephemeral_data
from app.tasks.collect_ephemeral import run as run_collect_ephemeral
from app.tasks.init_data import run as run_init_data
from app.tasks.red_for_n_days import run as run_red_for_n_days

TaskFn = Callable[..., dict[str, Any]]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ashare-platform", description="A-share platform backend CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect-ephemeral", help="Collect short-lived source data")
    collect.add_argument("--date", dest="trade_date")
    collect.add_argument("--news-count", type=int, default=20)
    collect.add_argument("--taoguba-count", type=int, default=20)
    collect.add_argument("--no-scan-trends", action="store_true")
    collect.add_argument("--popularity-max", type=int, default=1000)

    collect_all = subparsers.add_parser(
        "collect-all",
        help="Collect and build retained platform data for one trading day",
    )
    collect_all.add_argument("--date", dest="trade_date")
    collect_all.add_argument("--with-ephemeral", action="store_true")
    collect_all.add_argument("--news-count", type=int, default=20)
    collect_all.add_argument("--taoguba-count", type=int, default=20)
    collect_all.add_argument("--no-scan-trends", action="store_true")
    collect_all.add_argument("--popularity-max", type=int, default=1000)
    collect_all.add_argument("--trend-max-rank", type=int, default=1000)

    init_data = subparsers.add_parser(
        "init-data",
        help="Backfill recent trading days without running analysis steps",
    )
    init_data.add_argument("--date", dest="trade_date")
    init_data.add_argument("--days", type=int, default=30)

    trend = subparsers.add_parser("build-trend-pool", help="Build retained trend pool daily facts")
    trend.add_argument("--date", dest="trade_date")
    trend.add_argument("--max-rank", type=int, default=1000)

    theme = subparsers.add_parser("build-theme-pool", help="Build retained theme pool daily facts")
    theme.add_argument("--date", dest="trade_date")

    emotion = subparsers.add_parser("build-emotion-facts", help="Build retained market and theme emotion facts")
    emotion.add_argument("--date", dest="trade_date")

    review = subparsers.add_parser("build-market-review", help="Build retained daily market review")
    review.add_argument("--date", dest="trade_date")

    cleanup = subparsers.add_parser("cleanup-ephemeral-data", help="Clean expired ephemeral files")
    cleanup.add_argument("--max-age-days", type=int, default=3)

    red = subparsers.add_parser(
        "red-for-n-days",
        help="Screen Eastmoney popularity names whose last N trading days close at or above open",
    )
    red.add_argument("--date", dest="trade_date")
    red.add_argument("--days", type=int, default=7)
    red.add_argument("--top-n", type=int, default=1000)

    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "collect-ephemeral":
        return run_collect_ephemeral(
            trade_date=args.trade_date,
            news_count=args.news_count,
            taoguba_count=args.taoguba_count,
            scan_trends=not args.no_scan_trends,
            popularity_max=args.popularity_max,
        )
    if args.command == "collect-all":
        return run_collect_all(
            trade_date=args.trade_date,
            with_ephemeral=args.with_ephemeral,
            news_count=args.news_count,
            taoguba_count=args.taoguba_count,
            scan_trends=not args.no_scan_trends,
            popularity_max=args.popularity_max,
            trend_max_rank=args.trend_max_rank,
        )
    if args.command == "init-data":
        return run_init_data(
            trade_date=args.trade_date,
            days=args.days,
        )
    if args.command == "build-trend-pool":
        return run_build_trend_pool(
            trade_date=args.trade_date,
            max_rank=args.max_rank,
        )
    if args.command == "build-theme-pool":
        return run_build_theme_pool(trade_date=args.trade_date)
    if args.command == "build-emotion-facts":
        return run_build_emotion_facts(trade_date=args.trade_date)
    if args.command == "build-market-review":
        return run_build_market_review(trade_date=args.trade_date)
    if args.command == "cleanup-ephemeral-data":
        return run_cleanup_ephemeral_data(max_age_days=args.max_age_days)
    if args.command == "red-for-n-days":
        return run_red_for_n_days(
            trade_date=args.trade_date,
            days=args.days,
            top_n=args.top_n,
        )
    raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    """Run the backend CLI."""
    parser = _build_parser()
    args = parser.parse_args()
    result = _dispatch(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
