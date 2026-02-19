#!/usr/bin/env python3
"""A股复盘数据采集主入口。

并发调用各数据源 fetcher，将结果写入独立 JSON 文件。
单个数据源失败不影响其他源。

用法:
    python3 scripts/collect_sentiment.py \
        --output-dir /tmp/review/2026-02-17 \
        --news-count 20 \
        --taoguba-count 20
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 把 scripts 所在目录加入 sys.path，以便按包导入 ──
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from scripts.fetchers.trade_date import fetch_trade_date          # noqa: E402
from scripts.fetchers.news import (                               # noqa: E402
    fetch_headline, fetch_realtime, fetch_opportunity,
    fetch_daily_finance, fetch_news_flash,
)
from scripts.fetchers.market_overview import (                    # noqa: E402
    fetch_market_sectors_top_n,
)
from scripts.fetchers.taoguba import (                            # noqa: E402
    fetch_taoguba_hot,
    fetch_taoguba_hot_discussion,
    fetch_taoguba_now_recommend,
)
from scripts.fetchers.trend_scanner import (                     # noqa: E402
    fetch_eastmoney_top200, fetch_ths_snapshot, fetch_ths_history,
    scan_all, format_report_md, format_ths_md,
)
from scripts.fetchers.broker_account import fetch_broker_account  # noqa: E402


def _log(msg: str) -> None:
    print(f"[collect] {msg}", file=sys.stderr, flush=True)


# ── 数据精简函数 ──────────────────────────────────────


_NEWS_KEEP_FIELDS = {"title", "makeDate", "summary", "emotion", "detail"}


def _slim_news(data: list | dict) -> list | dict:
    """新闻数据只保留 title/makeDate/summary/emotion/detail。"""
    if isinstance(data, list):
        return [{k: v for k, v in item.items() if k in _NEWS_KEEP_FIELDS}
                for item in data]
    if isinstance(data, dict) and "data" in data:
        data["data"] = _slim_news(data["data"])
    return data


_TREND_KEEP_FIELDS = {
    "code", "name", "sc", "rank", "source",
    "is_uptrend", "star_rating", "score_total_100",
    "emotion_level", "emotion_label", "emotion_color", "emotion_reason",
    "trade_signal", "trade_signal_reason",
    "gain_30_pct", "gain_60_pct", "holding_experience", "reason",
}


def _slim_trend_results(data: dict) -> dict:
    """趋势扫描结果每只股票只保留关键字段。"""
    if "all_results" in data:
        data["all_results"] = [
            {k: v for k, v in item.items() if k in _TREND_KEEP_FIELDS}
            for item in data["all_results"]
        ]
    return data


# ── 采集任务定义 ──────────────────────────────────────


def _make_tasks(news_count: int, taoguba_count: int) -> list[dict]:
    """返回采集任务列表，每项包含 name / filename / fn。"""
    return [
        {"name": "trade_date",       "filename": "trade_date.json",       "fn": fetch_trade_date},
        {"name": "news_headline",    "filename": "news_headline.json",    "fn": lambda: fetch_headline(news_count, fetch_body=True)},
        {"name": "news_realtime",    "filename": "news_realtime.json",    "fn": lambda: fetch_realtime(news_count, fetch_body=True)},
        {"name": "news_opportunity", "filename": "news_opportunity.json", "fn": lambda: fetch_opportunity(news_count, fetch_body=True)},
        {"name": "news_daily",       "filename": "news_daily.json",       "fn": lambda: fetch_daily_finance(news_count, fetch_body=True)},
        {"name": "news_flash",       "filename": "news_flash.json",       "fn": lambda: fetch_news_flash(news_count)},
        {"name": "market_sectors",   "filename": "market_sectors.json",   "fn": lambda: fetch_market_sectors_top_n(5)},
        {"name": "taoguba_hot",      "filename": "taoguba_hot.json",      "fn": lambda: fetch_taoguba_hot(taoguba_count)},
        {"name": "taoguba_hot_discussion", "filename": "taoguba_hot_discussion.json",
         "fn": lambda: fetch_taoguba_hot_discussion(page_no=1, count=taoguba_count)},
        {"name": "taoguba_recommend", "filename": "taoguba_recommend.json",
         "fn": lambda: fetch_taoguba_now_recommend(count=taoguba_count)},
    ]


# ── 主逻辑 ────────────────────────────────────────────


def collect(
    output_dir: str,
    news_count: int = 20,
    taoguba_count: int = 20,
    *,
    scan_trends: bool = True,
    popularity_max: int = 200,
    fetch_broker: bool = False,
) -> dict:
    """执行全量数据采集，返回 summary dict。

    Parameters
    ----------
    scan_trends : bool
        是否执行趋势扫描（默认 True）。扫描200只股约2-3分钟。
    popularity_max : int
        东方财富人气榜扫描上限（默认200，最大200）。
    fetch_broker : bool
        是否采集 jvQuant 账户持仓数据（默认 False）。
        需配置 ~/.openclaw/jvquant.json 或对应环境变量。
        注意：每次登录有计费，模块内部已实现 ticket 缓存复用。
    """
    os.makedirs(output_dir, exist_ok=True)
    tasks = _make_tasks(news_count, taoguba_count)
    summary: dict = {"sources": {}, "output_dir": output_dir}
    t0 = time.time()

    def _run(task: dict) -> tuple[str, str, object, float]:
        name = task["name"]
        start = time.time()
        try:
            data = task["fn"]()
            elapsed = time.time() - start
            return name, "ok", data, elapsed
        except Exception as exc:
            elapsed = time.time() - start
            return name, "error", str(exc), elapsed

    # 并发采集（淘股吧本身内部也有并发，给 4 个 worker 即可）
    results: dict[str, tuple] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_run, t): t for t in tasks}
        for future in as_completed(futures):
            name, status, data, elapsed = future.result()
            results[name] = (status, data, elapsed)
            icon = "\u2713" if status == "ok" else "\u2717"
            _log(f"  {icon} {name} ({elapsed:.1f}s)")

    # ── 券商账户采集（可选，独立执行，失败不影响主流程） ──
    if fetch_broker:
        _log("采集券商账户数据（jvQuant）...")
        broker_t0 = time.time()
        try:
            broker_data = fetch_broker_account()
            broker_elapsed = time.time() - broker_t0
            results["broker_account"] = ("ok", broker_data, broker_elapsed)
            reused = broker_data.get("ticket_reused", False)
            _log(f"  ✓ broker_account ({broker_elapsed:.1f}s)"
                 f"{'，复用缓存ticket（未计费）' if reused else '，已重新登录'}")
        except Exception as exc:
            broker_elapsed = time.time() - broker_t0
            results["broker_account"] = ("error", str(exc), broker_elapsed)
            _log(f"  ✗ broker_account ({broker_elapsed:.1f}s): {exc}")

    # ── 趋势扫描（耗时较长，独立于上面的并发池） ──
    if scan_trends:
        _log("开始趋势扫描...")
        scan_t0 = time.time()

        # 取最近交易日（优先用已采集结果，避免重复请求）
        _td_result = results.get("trade_date")
        _last_trade_date: str | None = None
        if _td_result and _td_result[0] == "ok":
            _raw = _td_result[1]
            _last_trade_date = _raw if isinstance(_raw, str) else None

        try:
            # 1) 拉取人气榜
            candidates = fetch_eastmoney_top200(max_rank=min(200, popularity_max))
            _log(f"  人气榜候选: {len(candidates)} 只")

            # 2) 同花顺快照（传入最近交易日，避免假期取到空数据）
            ths = fetch_ths_snapshot(end_date=_last_trade_date)
            results["ths_snapshot"] = ("ok", ths, time.time() - scan_t0)
            _log(f"  \u2713 ths_snapshot ({time.time() - scan_t0:.1f}s, date={ths.get('date')})")

            # 3) 同花顺历史（最近5个交易日）
            ths_hist = fetch_ths_history(days=5, end_date=_last_trade_date)
            results["ths_history"] = ("ok", {"days": len(ths_hist), "history": ths_hist},
                                      time.time() - scan_t0)
            _log(f"  \u2713 ths_history ({len(ths_hist)} \u5929)")

            # 生成 ths_report.md（结构化 Markdown，供 LLM 直接阅读）
            ths_md = format_ths_md(ths, ths_hist)
            ths_report_path = os.path.join(output_dir, "ths_report.md")
            with open(ths_report_path, "w", encoding="utf-8") as f:
                f.write(ths_md)
            _log(f"  \u2713 ths_report.md \u5df2\u751f\u6210")

            # 4) 并发 K 线扫描 + 评分
            trend_results = scan_all(candidates, workers=10)
            scan_elapsed = time.time() - scan_t0
            _log(f"  \u2713 trend_scan: {len(trend_results)} \u53ea, "
                 f"\u8d8b\u52bf\u80a1 {sum(1 for r in trend_results if r.is_uptrend)} \u53ea ({scan_elapsed:.1f}s)")

            # 包装输出
            results["trend_scan"] = (
                "ok",
                {
                    "eastmoney_count": len(candidates),
                    "ths_date": ths.get("date"),
                    "scanned": len(trend_results),
                    "uptrend_count": sum(1 for r in trend_results if r.is_uptrend),
                    "all_results": [r.to_dict() for r in trend_results],
                },
                scan_elapsed,
            )

            # 生成 trend_report.md
            report_md = format_report_md(
                trend_results,
                eastmoney_count=len(candidates),
                ths_date=ths.get("date"),
            )
            report_path = os.path.join(output_dir, "trend_report.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)

        except Exception as exc:
            scan_elapsed = time.time() - scan_t0
            results["trend_scan"] = ("error", str(exc), scan_elapsed)
            _log(f"  \u2717 trend_scan ({scan_elapsed:.1f}s): {exc}")

    # 写入文件
    name_to_file = {t["name"]: t["filename"] for t in tasks}
    # 追加趋势扫描、券商账户的文件映射
    name_to_file["ths_snapshot"] = "ths_snapshot.json"
    name_to_file["ths_history"] = "ths_history.json"
    name_to_file["trend_scan"] = "trend_scan.json"
    name_to_file["broker_account"] = "broker_account.json"

    for name, (status, data, elapsed) in results.items():
        filename = name_to_file.get(name)
        if not filename:
            continue
        filepath = os.path.join(output_dir, filename)

        if status == "ok":
            if isinstance(data, str):
                data = {"trade_date": data}
            # 写入前精简数据
            if name.startswith("news_"):
                data = _slim_news(data)
            elif name == "trend_scan":
                data = _slim_trend_results(data)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        count = "-"
        if status == "ok":
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                if "top_inflow" in data:
                    count = data.get("sector_count", "-")
                elif "all_results" in data:
                    count = data.get("uptrend_count", len(data["all_results"]))

        summary["sources"][name] = {
            "status": status,
            "file": filename if status == "ok" else None,
            "count": count,
            "elapsed_sec": round(elapsed, 2),
            "error": data if status == "error" else None,
        }

    total_elapsed = time.time() - t0
    summary["total_elapsed_sec"] = round(total_elapsed, 2)
    summary["ok_count"] = sum(1 for v in summary["sources"].values() if v["status"] == "ok")
    summary["error_count"] = sum(1 for v in summary["sources"].values() if v["status"] == "error")

    # 写 summary
    summary_path = os.path.join(output_dir, "collection_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


# ── CLI 入口 ──────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="A股复盘数据采集")
    parser.add_argument("--output-dir", required=True, help="数据输出目录")
    parser.add_argument("--news-count", type=int, default=20, help="每类新闻条数")
    parser.add_argument("--taoguba-count", type=int, default=20, help="淘股吧帖子数")
    parser.add_argument("--no-scan-trends", action="store_true", help="跳过趋势扫描")
    parser.add_argument("--popularity-max", type=int, default=200, help="人气榜扫描上限(<=200)")
    parser.add_argument("--broker", action="store_true",
                        help="采集 jvQuant 账户持仓数据（需配置 ~/.openclaw/jvquant.json）")
    args = parser.parse_args()

    _log(f"开始采集 -> {args.output_dir}")
    summary = collect(
        args.output_dir, args.news_count, args.taoguba_count,
        scan_trends=not args.no_scan_trends,
        popularity_max=args.popularity_max,
        fetch_broker=args.broker,
    )
    _log(f"完成: {summary['ok_count']} 成功, {summary['error_count']} 失败, "
         f"耗时 {summary['total_elapsed_sec']}s")

    if summary["error_count"] > 0:
        for name, info in summary["sources"].items():
            if info["status"] == "error":
                _log(f"  失败: {name} - {info['error']}")


if __name__ == "__main__":
    main()
