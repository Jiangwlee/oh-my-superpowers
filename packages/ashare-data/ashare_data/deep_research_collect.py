"""个股深研数据采集服务。

从趋势股 + watchlist 确定目标，按时效策略过滤后并发采集。
纯数据采集，不含 LLM 调用。

供 task-runner 端点 POST /ashare/deep-research/collect 调用。
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ashare_data.core.config import ASHARE_HOME, DATA_DIR
from ashare_data.core.watchlist import load as load_watchlist
from ashare_data.deep_research import DeepResearchArchive, normalize_full_code
from ashare_data.fetchers.eastmoney_guba import (
    fetch_latest_posts,
    fetch_post_detail,
    fetch_stock_info_list,
    fetch_stock_notice_list,
)
from ashare_data.fetchers.taoguba import (
    fetch_taoguba_quotes_posts,
    fetch_taoguba_stock_tags,
    fetch_taoguba_zh_recommend,
)

logger = logging.getLogger(__name__)

_DEFAULT_ARCHIVE_DIR = ASHARE_HOME / "deep_research"


def _find_latest_data_dir() -> Path | None:
    """找到最新的每日数据目录。"""
    if not DATA_DIR.exists():
        return None
    dirs = sorted(
        [d for d in DATA_DIR.iterdir() if d.is_dir() and len(d.name) == 10],
        reverse=True,
    )
    return dirs[0] if dirs else None


def _load_trend_targets(data_dir: Path) -> list[dict[str, str]]:
    """从 trend_scan.json 读取趋势股。"""
    trend_path = data_dir / "raw" / "trend_scan.json"
    if not trend_path.exists():
        return []
    try:
        data = json.loads(trend_path.read_text(encoding="utf-8"))
        results = data.get("all_results", [])
        return [
            {"code": r["code"], "name": r.get("name", "")}
            for r in results
            if r.get("is_uptrend")
        ]
    except Exception:
        logger.exception("读取 trend_scan.json 失败")
        return []


def _load_watchlist_codes() -> list[dict[str, str]]:
    """从 watchlist 读取股票。"""
    stocks = load_watchlist()
    return [
        {"code": str(s.get("code", "")), "name": str(s.get("name", ""))}
        for s in stocks
        if s.get("code") and s.get("status") == "active"
    ]


def _fetch_em_data(
    code: str,
    *,
    post_limit: int = 36,
    detail_limit: int = 5,
    notice_days: int = 3,
) -> dict[str, Any]:
    """采集东方财富股吧数据。"""
    posts = fetch_latest_posts(code, limit=post_limit)
    infos = fetch_stock_info_list(code)
    notices = fetch_stock_notice_list(code, recent_days=notice_days)

    detail_posts = []
    for item in posts[:max(0, detail_limit)]:
        post_id = item.get("post_id")
        if not post_id:
            continue
        try:
            detail_posts.append(fetch_post_detail(code, str(post_id)))
        except Exception as exc:
            detail_posts.append({"post_id": str(post_id), "error": str(exc)})

    return {
        "code": code,
        "latest_posts": posts,
        "latest_post_details": detail_posts,
        "stock_infos": infos,
        "stock_notices_recent": notices,
    }


def _fetch_tgb_data(
    code: str,
    *,
    quotes_count: int = 8,
    zh_page: int = 1,
    zh_count: int = 20,
) -> dict[str, Any]:
    """采集淘股吧个股数据。"""
    full_code = normalize_full_code(code)
    tags = fetch_taoguba_stock_tags(full_code)
    quotes_posts = fetch_taoguba_quotes_posts(full_code, count=quotes_count)
    zh_recommend = fetch_taoguba_zh_recommend(page_no=zh_page, count=zh_count)

    return {
        "full_code": full_code,
        "stock_tags": tags,
        "quotes_posts": quotes_posts,
        "zh_recommend": zh_recommend,
    }


def _collect_one_stock(
    code: str,
    name: str,
    archive: DeepResearchArchive,
) -> dict[str, Any]:
    """采集单只股票的深研数据。"""
    import random
    
    start = time.monotonic()
    try:
        # 添加随机延迟避免请求风暴
        time.sleep(random.uniform(0.1, 0.3))
        em_data = _fetch_em_data(code)
        tgb_data = _fetch_tgb_data(code)
        archive.save_raw_data(code, name, em_data, tgb_data)
        elapsed = round(time.monotonic() - start, 2)
        return {"code": code, "name": name, "status": "collected", "elapsed_sec": elapsed}
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 2)
        logger.exception("采集 %s 失败", code)
        return {
            "code": code, "name": name, "status": "error",
            "error": str(exc), "elapsed_sec": elapsed,
        }


def collect_deep_research(
    *,
    archive_dir: Path | None = None,
    force: bool = False,
    max_workers: int = 3,  # 降低并发避免淘股吧 HTTP 错误
) -> dict[str, Any]:
    """执行深研数据采集。

    Args:
        archive_dir: 档案存储目录，默认 ~/.ashare-assistant/deep_research/
        force: 忽略 7 天时效限制。
        max_workers: 并发 worker 数。

    Returns:
        {"ok": bool, "stocks": [...], "collected_count": int, "skipped_count": int, "total_targets": int}
    """
    archive = DeepResearchArchive(archive_dir or _DEFAULT_ARCHIVE_DIR)
    start = time.monotonic()

    # 1. 确定目标
    data_dir = _find_latest_data_dir()
    watchlist_targets = _load_watchlist_codes()

    if data_dir is None and not watchlist_targets:
        return {
            "ok": False,
            "error": "no_data_dir_and_no_watchlist",
            "stocks": [],
            "collected_count": 0,
            "skipped_count": 0,
            "total_targets": 0,
        }

    trend_targets = _load_trend_targets(data_dir) if data_dir else []

    # 2. 合并去重
    seen: set[str] = set()
    all_targets: list[dict[str, str]] = []
    for t in trend_targets + watchlist_targets:
        code = t["code"]
        if code not in seen:
            seen.add(code)
            all_targets.append(t)

    if not all_targets:
        return {
            "ok": True,
            "stocks": [],
            "collected_count": 0,
            "skipped_count": 0,
            "total_targets": 0,
        }

    # 3. 按时效过滤
    to_collect: list[dict[str, str]] = []
    stocks_result: list[dict[str, Any]] = []
    for t in all_targets:
        code = t["code"]
        if archive.needs_update(code, force=force):
            to_collect.append(t)
        else:
            stocks_result.append({
                "code": code, "name": t["name"],
                "status": "skipped", "reason": "fresh",
            })

    # 4. 并发采集
    if to_collect:
        pool_size = max(1, min(max_workers, len(to_collect)))
        with ThreadPoolExecutor(max_workers=pool_size) as pool:
            futures = {
                pool.submit(_collect_one_stock, t["code"], t["name"], archive): t["code"]
                for t in to_collect
            }
            for future in as_completed(futures):
                stocks_result.append(future.result())

    collected = sum(1 for s in stocks_result if s["status"] == "collected")
    skipped = sum(1 for s in stocks_result if s["status"] == "skipped")
    elapsed = round(time.monotonic() - start, 2)

    return {
        "ok": True,
        "stocks": stocks_result,
        "collected_count": collected,
        "skipped_count": skipped,
        "total_targets": len(all_targets),
        "elapsed_sec": elapsed,
    }
