#!/usr/bin/env python3
"""ashare-data 定时采集入口（cron 调用此脚本）。

流程：
  1. collect   — 并发拉取所有数据源，写入 {data_dir}/raw/
  2. filter    — 将 raw/ JSON 过滤转换为 {data_dir}/filtered/ Markdown
  3. sentiment — 生成 report/news_sentiment.md 与 report/social_sentiment.md

用法：
    # 采集今日数据（最常用）
    python3 -m ashare_data.collect

    # 补采指定日期
    python3 -m ashare_data.collect --date 2026-02-25

    # 仅补跑 filter（raw/ 已存在）
    python3 -m ashare_data.collect --skip-collect

    # 仅补采 raw/（不重跑 filter）
    python3 -m ashare_data.collect --skip-filter

cron 示例（每日 22:05 盘后采集）：
    5 22 * * 1-5  /usr/bin/python3 -m ashare_data.collect >> /var/log/ashare-data.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from ashare_data.core.config import DATA_DIR, ensure_dirs
from ashare_data.collect_sentiment import collect
from ashare_data.filter_to_markdown import filter_all

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))


def _today_cn() -> str:
    return datetime.now(_CN_TZ).strftime("%Y-%m-%d")


def run(
    date_str: str | None = None,
    skip_collect: bool = False,
    skip_filter: bool = False,
    news_count: int = 20,
    taoguba_count: int = 20,
    scan_trends: bool = True,
    popularity_max: int = 1000,
) -> dict[str, Any]:
    """执行完整采集流水线。

    Args:
        date_str:       目标日期（YYYY-MM-DD），默认今日。
        skip_collect:   跳过数据采集，只跑 filter。
        skip_filter:    跳过 filter，只跑数据采集。
        news_count:     每类新闻条数。
        taoguba_count:  淘股吧帖子数。
        scan_trends:    是否执行趋势扫描。
        popularity_max: 人气榜扫描上限。
        Returns:
        {"ok": bool, "data_dir": str, "collect": dict | None, "filter": dict | None, "sentiment": dict | None, "error": str | None}
    """
    ensure_dirs()
    date_str = date_str or _today_cn()
    data_dir = DATA_DIR / date_str
    raw_dir = data_dir / "raw"
    filtered_dir = data_dir / "filtered"

    logger.info("日期：%s  数据目录：%s", date_str, data_dir)

    result: dict[str, Any] = {
        "ok": True,
        "data_dir": str(data_dir),
        "collect": None,
        "filter": None,
        "error": None,
    }

    # ── 阶段 1: 数据采集 ──────────────────────────────────────────
    if not skip_collect:
        logger.info("[collect] 开始采集 -> %s", raw_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)
        try:
            summary = collect(
                str(raw_dir),
                news_count=news_count,
                taoguba_count=taoguba_count,
                scan_trends=scan_trends,
                popularity_max=popularity_max,
            )
            ok = summary["ok_count"]
            err = summary["error_count"]
            elapsed = summary["total_elapsed_sec"]
            logger.info("[collect] 完成：%d 成功，%d 失败，%.1fs", ok, err, elapsed)
            if err > 0:
                for name, info in summary["sources"].items():
                    if info["status"] == "error":
                        logger.warning("[collect] 失败：%s — %s", name, info["error"])
            result["collect"] = {
                "ok_count": ok,
                "error_count": err,
                "total_elapsed_sec": elapsed,
            }
            if err > 0:
                result["ok"] = False
        except RuntimeError as exc:
            logger.error("[collect] 中止：%s", exc)
            result["ok"] = False
            result["error"] = str(exc)
            return result
    else:
        logger.info("[collect] 已跳过（--skip-collect）")

    # ── 阶段 2: 过滤转换 ──────────────────────────────────────────
    if not skip_filter:
        if not raw_dir.exists():
            logger.error("[filter] raw/ 目录不存在，请先运行 collect: %s", raw_dir)
            result["ok"] = False
            return result
        logger.info("[filter] 开始转换 %s -> %s", raw_dir, filtered_dir)
        filtered_dir.mkdir(parents=True, exist_ok=True)
        try:
            filter_result = filter_all(str(raw_dir), str(filtered_dir))
            logger.info(
                "[filter] 完成：%d 转换，%d 跳过，%d 失败，%.1f KB",
                filter_result["converted"],
                filter_result["skipped"],
                filter_result["errors"],
                filter_result["total_size_kb"],
            )
            result["filter"] = {
                "converted": filter_result["converted"],
                "skipped": filter_result["skipped"],
                "errors": filter_result["errors"],
                "total_size_kb": filter_result["total_size_kb"],
            }
            if filter_result["errors"] > 0:
                result["ok"] = False
        except Exception as exc:
            logger.exception("[filter] 异常：%s", exc)
            result["ok"] = False
            result["error"] = str(exc)
            return result
    else:
        logger.info("[filter] 已跳过（--skip-filter）")

    # ── 阶段 3: 情绪预处理（news/social） ────────────────────────

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ashare-data 定时采集入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--date", help="目标日期 YYYY-MM-DD（默认今日）")
    parser.add_argument("--skip-collect", action="store_true", help="跳过数据采集")
    parser.add_argument("--skip-filter", action="store_true", help="跳过 filter 转换")
    parser.add_argument("--news-count", type=int, default=20, help="每类新闻条数")
    parser.add_argument("--taoguba-count", type=int, default=20, help="淘股吧帖子数")
    parser.add_argument(
        "--no-scan-trends", action="store_true", help="跳过趋势扫描（加快调试）"
    )
    parser.add_argument(
        "--popularity-max", type=int, default=1000, help="人气榜扫描上限"
    )
    parser.add_argument("--verbose", action="store_true", help="详细日志")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [ashare-data] %(message)s",
        datefmt="%H:%M:%S",
    )

    result = run(
        date_str=args.date,
        skip_collect=args.skip_collect,
        skip_filter=args.skip_filter,
        news_count=args.news_count,
        taoguba_count=args.taoguba_count,
        scan_trends=not args.no_scan_trends,
        popularity_max=args.popularity_max,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
