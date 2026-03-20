#!/usr/bin/env python3
"""A股复盘数据采集主入口。

并发调用各数据源 fetcher，将结果写入独立 JSON 文件。
单个数据源失败不影响其他源。

券商账户数据（jvQuant）自动采集规则：
  - 若 ~/.ashare-data/jvquant.json 存在，则自动采集账户持仓数据。
  - 若采集失败，脚本以非零退出码终止，并在 stderr 输出明确错误信息。
  - 若 ~/.ashare-data/jvquant.json 不存在，跳过采集并打印提示（不报错）。

用法:
    python3 scripts/collect_sentiment.py \
        --output-dir ~/.ashare-assistant/data/2026-02-17 \
        --news-count 20 \
        --taoguba-count 20
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── 把 scripts 所在目录加入 sys.path，以便按包导入 ──
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from ashare_data.fetchers.trade_date import fetch_trade_date  # noqa: E402
from ashare_data.fetchers.news import (  # noqa: E402
    fetch_headline,
    fetch_realtime,
    fetch_opportunity,
    fetch_daily_finance,
    fetch_news_flash,
)
from ashare_data.fetchers.market_overview import (  # noqa: E402
    fetch_market_sectors_top_n,
)
from ashare_data.fetchers.funding import fetch_funding, fetch_funding_for_codes  # noqa: E402
from ashare_data.fetchers.taoguba import (  # noqa: E402
    fetch_taoguba_hot,
    fetch_taoguba_hot_discussion,
    fetch_taoguba_now_recommend,
)
from ashare_data.fetchers.trend_scanner import (  # noqa: E402
    fetch_eastmoney_popularity_rank,
    fetch_ths_snapshot,
    fetch_ths_history,
    scan_all,
    format_report_md,
    format_ths_md,
)
from ashare_data.fetchers.broker_account import fetch_broker_account  # noqa: E402
from ashare_data.fetchers.us_market import fetch_us_market  # noqa: E402
from ashare_data.core.cache import cache_cleanup  # noqa: E402
from ashare_data.core.config import ensure_dirs  # noqa: E402
from ashare_data.core.config import ASHARE_HOME  # noqa: E402
from ashare_data.core.utils import atomic_write_json, atomic_write_text  # noqa: E402
from ashare_data.core.watchlist import (  # noqa: E402
    get_extra_candidates,
    load as load_watchlist,
    update_from_scan,
)
def _log(msg: str) -> None:
    print(f"[collect] {msg}", file=sys.stderr, flush=True)


_RAW_SCHEMA_VERSION = "1.0"
_SUMMARY_SCHEMA_VERSION = "1.1"
_RUN_ID_SCHEMA_VERSION = "1.0"


def _extract_rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "decisions", "signals"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _calc_missing_key_rate(rows: list[dict], required_keys: set[str]) -> float | None:
    if not rows or not required_keys:
        return None
    total = len(rows) * len(required_keys)
    missing = 0
    for row in rows:
        for key in required_keys:
            value = row.get(key)
            if value is None or value == "":
                missing += 1
    return round(missing / total, 4)


def _calc_freshness_sec(rows: list[dict], now_ts: float) -> int | None:
    if not rows:
        return None
    for field in ("makeDate", "date", "time", "fetched_at", "generated_at"):
        raw = rows[0].get(field)
        if not raw:
            continue
        if isinstance(raw, (int, float)):
            # 20260217 (YYYYMMDD) 或秒级时间戳
            text = str(int(raw))
            if len(text) == 8:
                try:
                    dt = datetime.strptime(text, "%Y%m%d")
                    return int(max(0, now_ts - dt.timestamp()))
                except ValueError:
                    continue
            if len(text) >= 10:
                return int(max(0, now_ts - float(raw)))
        if isinstance(raw, str):
            text = raw.strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
                try:
                    dt = datetime.strptime(text, fmt)
                    return int(max(0, now_ts - dt.timestamp()))
                except ValueError:
                    continue
    return None


def _build_dq(name: str, payload: object, status: str, now_ts: float) -> dict[str, float | int | bool | None]:
    if status != "ok":
        return {"record_count": None, "is_empty": None, "freshness_sec": None, "missing_key_rate": None}
    rows = _extract_rows(payload)
    required_by_source: dict[str, set[str]] = {
        "news_headline": {"title", "makeDate", "detail"},
        "news_realtime": {"title", "makeDate", "detail"},
        "news_opportunity": {"title", "makeDate", "detail"},
        "news_daily": {"title", "makeDate", "detail"},
        "news_flash": {"title", "makeDate"},
        "taoguba_hot": {"title", "date"},
        "taoguba_hot_discussion": {"subject", "author"},
        "taoguba_recommend": {"subject", "author"},
    }
    required = required_by_source.get(name, set())
    count: int | None = None
    if isinstance(payload, list):
        count = len(payload)
    elif isinstance(payload, dict):
        if rows:
            count = len(rows)
        else:
            count = 1
    return {
        "record_count": count,
        "is_empty": (count == 0) if count is not None else None,
        "freshness_sec": _calc_freshness_sec(rows, now_ts),
        "missing_key_rate": _calc_missing_key_rate(rows, required),
    }


def _read_strategy_version(skill_root: str) -> tuple[str, bool]:
    """从 active.yaml 读取策略版本。"""
    strategy_path = os.path.join(skill_root, "strategy", "active.yaml")
    try:
        with open(strategy_path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return "v0", True

    for line in lines:
        striped = line.strip()
        if striped.startswith("strategy_version:"):
            value = striped.split(":", 1)[1].strip().strip("\"'")
            if value:
                return value, False
    for line in lines:
        striped = line.strip()
        if striped.startswith("version:"):
            value = striped.split(":", 1)[1].strip().strip("\"'")
            if value:
                return value, False
    return "v0", True


def _extract_as_of_date(output_dir: str) -> str:
    """从输出目录推断 YYYY-MM-DD 日期。"""
    base = os.path.basename(output_dir.rstrip("/"))
    if len(base) == 10 and base[4] == "-" and base[7] == "-":
        return base
    return datetime.now().strftime("%Y-%m-%d")


def _build_run_id(as_of_date: str, strategy_version: str) -> str:
    """生成 run_id。"""
    date_part = as_of_date.replace("-", "")
    time_part = datetime.now().strftime("%H%M%S")
    return f"{date_part}-{strategy_version}-{time_part}"


def _resolve_data_dir(output_dir: str) -> str:
    """从 raw 目录推断数据根目录。"""
    base = os.path.basename(output_dir.rstrip("/"))
    if base == "raw":
        return os.path.dirname(output_dir.rstrip("/"))
    return output_dir


def _get_result_attr(obj: object, attr: str, default: object = None) -> object:
    if hasattr(obj, attr):
        return getattr(obj, attr)
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return default



# ── 数据精简函数 ──────────────────────────────────────


_NEWS_KEEP_FIELDS = {"title", "makeDate", "summary", "emotion", "detail"}


def _slim_news(data: list | dict) -> list | dict:
    """新闻数据只保留 title/makeDate/summary/emotion/detail。"""
    if isinstance(data, list):
        return [
            {k: v for k, v in item.items() if k in _NEWS_KEEP_FIELDS} for item in data
        ]
    if isinstance(data, dict) and "data" in data:
        data["data"] = _slim_news(data["data"])
    return data


_TREND_KEEP_FIELDS = {
    "code",
    "name",
    "sc",
    "rank",
    "source",
    "is_uptrend",
    "star_rating",
    "score_total_100",
    "emotion_level",
    "emotion_label",
    "emotion_color",
    "emotion_reason",
    "trade_signal",
    "trade_signal_reason",
    "gain_30_pct",
    "gain_60_pct",
    "holding_experience",
    "reason",
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
        {"name": "trade_date", "filename": "trade_date.json", "fn": fetch_trade_date},
        {
            "name": "news_headline",
            "filename": "news_headline.json",
            "fn": lambda: fetch_headline(news_count, fetch_body=True),
        },
        {
            "name": "news_realtime",
            "filename": "news_realtime.json",
            "fn": lambda: fetch_realtime(news_count, fetch_body=True),
        },
        {
            "name": "news_opportunity",
            "filename": "news_opportunity.json",
            "fn": lambda: fetch_opportunity(news_count, fetch_body=True),
        },
        {
            "name": "news_daily",
            "filename": "news_daily.json",
            "fn": lambda: fetch_daily_finance(news_count, fetch_body=True),
        },
        {
            "name": "news_flash",
            "filename": "news_flash.json",
            "fn": lambda: fetch_news_flash(news_count),
        },
        {
            "name": "market_sectors",
            "filename": "market_sectors.json",
            "fn": lambda: fetch_market_sectors_top_n(5),
        },
        {"name": "funding", "filename": "funding.json", "fn": fetch_funding},
        {
            "name": "taoguba_hot",
            "filename": "taoguba_hot.json",
            "fn": lambda: fetch_taoguba_hot(taoguba_count),
        },
        {
            "name": "taoguba_hot_discussion",
            "filename": "taoguba_hot_discussion.json",
            "fn": lambda: fetch_taoguba_hot_discussion(page_no=1, count=taoguba_count),
        },
        {
            "name": "taoguba_recommend",
            "filename": "taoguba_recommend.json",
            "fn": lambda: fetch_taoguba_now_recommend(count=taoguba_count),
        },
        {"name": "us_market", "filename": "us_market.json", "fn": fetch_us_market},
    ]


# ── 主逻辑 ────────────────────────────────────────────


_JVQUANT_CONFIG_PATH = os.path.expanduser("~/.ashare-data/jvquant.json")


def _jvquant_configured() -> bool:
    """检测 jvQuant 是否已配置（配置文件存在即视为已配置）。"""
    return os.path.exists(_JVQUANT_CONFIG_PATH)


def collect(
    output_dir: str,
    news_count: int = 20,
    taoguba_count: int = 20,
    *,
    scan_trends: bool = True,
    popularity_max: int = 1000
) -> dict:
    """执行全量数据采集，返回 summary dict。

    券商账户数据（jvQuant）自动采集规则：
      - 若 ~/.ashare-data/jvquant.json 存在，则自动采集。
      - 若采集失败，直接抛出异常（调用方负责处理）。
      - 若配置文件不存在，跳过采集并在 summary 中记录 skipped 状态。

    Parameters
    ----------
    scan_trends : bool
        是否执行趋势扫描（默认 True）。扫描1000只股约8-12分钟。
    popularity_max : int
        东方财富人气榜扫描上限（默认1000，最大1000）。
    """
    ensure_dirs()
    try:
        cleanup_result = cache_cleanup(max_age_days=7)
        _log(f"cache cleanup: removed={cleanup_result.get('removed_files', 0)}")
    except Exception as exc:
        _log(f"cache cleanup skipped: {exc}")
    os.makedirs(output_dir, exist_ok=True)
    tasks = _make_tasks(news_count, taoguba_count)
    as_of_date = _extract_as_of_date(output_dir)
    strategy_version, strategy_version_fallback = _read_strategy_version(_SKILL_ROOT)
    run_id = _build_run_id(as_of_date, strategy_version)
    summary: dict = {
        "sources": {},
        "output_dir": output_dir,
        "as_of_date": as_of_date,
        "run_id": run_id,
        "strategy_version": strategy_version,
        "strategy_version_fallback": strategy_version_fallback,
    }
    t0 = time.time()
    now_ts = time.time()

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

    # ── 券商账户采集（自动检测，失败时抛出异常） ──
    if _jvquant_configured():
        _log("检测到 jvquant.json，开始采集券商账户数据...")
        broker_t0 = time.time()
        try:
            broker_data = fetch_broker_account()
            broker_elapsed = time.time() - broker_t0
            results["broker_account"] = ("ok", broker_data, broker_elapsed)
            reused = broker_data.get("ticket_reused", False)
            _log(
                f"  ✓ broker_account ({broker_elapsed:.1f}s)"
                f"{'，复用缓存ticket（未计费）' if reused else '，已重新登录'}"
            )
        except Exception as exc:
            broker_elapsed = time.time() - broker_t0
            _log(f"  ✗ broker_account ({broker_elapsed:.1f}s): {exc}")
            raise RuntimeError(
                f"jvQuant 账户数据采集失败：{exc}\n"
                f"请检查 {_JVQUANT_CONFIG_PATH} 配置是否正确，"
                f"或确认网络/API 凭证是否有效。\n"
                f"交易计划将无法生成，请解决后重新运行。"
            ) from exc
    else:
        _log(f"未检测到 {_JVQUANT_CONFIG_PATH}，跳过券商账户采集（将无法生成交易计划）")

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
            candidates = fetch_eastmoney_popularity_rank(top_n=min(1000, popularity_max))
            _log(f"  人气榜候选: {len(candidates)} 只")

            # 2) 同花顺快照（传入最近交易日，避免假期取到空数据）
            ths = fetch_ths_snapshot(end_date=_last_trade_date)
            results["ths_snapshot"] = ("ok", ths, time.time() - scan_t0)
            _log(
                f"  \u2713 ths_snapshot ({time.time() - scan_t0:.1f}s, date={ths.get('date')})"
            )

            # 3) 同花顺历史（最近5个交易日）
            ths_hist = fetch_ths_history(days=5, end_date=_last_trade_date)
            results["ths_history"] = (
                "ok",
                {"days": len(ths_hist), "history": ths_hist},
                time.time() - scan_t0,
            )
            _log(f"  \u2713 ths_history ({len(ths_hist)} \u5929)")

            # 生成 ths_report.md（结构化 Markdown，供 LLM 直接阅读）
            ths_md = format_ths_md(ths, ths_hist)
            ths_report_path = os.path.join(output_dir, "ths_report.md")
            atomic_write_text(ths_report_path, ths_md)
            _log(f"  \u2713 ths_report.md \u5df2\u751f\u6210")

            # 4) 合并 watchlist 额外候选（未在东方财富池中的股票）
            watchlist_extras = get_extra_candidates(
                exclude_codes={c["code"] for c in candidates}
            )
            if watchlist_extras:
                _log(f"  watchlist 补充: {len(watchlist_extras)} 只")
            all_candidates = candidates + watchlist_extras

            # 5) 并发 K 线扫描 + 评分
            trend_results = scan_all(all_candidates, workers=10)
            scan_elapsed = time.time() - scan_t0
            _log(
                f"  \u2713 trend_scan: {len(trend_results)} \u53ea, "
                f"\u8d8b\u52bf\u80a1 {sum(1 for r in trend_results if r.is_uptrend)} \u53ea ({scan_elapsed:.1f}s)"
            )

            # 6) 自动维护 watchlist
            update_from_scan(trend_results, as_of_date)

            # 7) 写 watchlist_scan.json（watchlist 股完整指标，不走 _slim）
            watchlist_stocks = load_watchlist()
            watchlist_codes = {str(s.get("code", "")) for s in watchlist_stocks if s.get("code")}
            if watchlist_codes:
                watchlist_scan_data = [
                    r.to_dict() for r in trend_results if r.code in watchlist_codes
                ]
                watchlist_scan_path = os.path.join(output_dir, "watchlist_scan.json")
                atomic_write_json(watchlist_scan_path, watchlist_scan_data)
                _log(f"  \u2713 watchlist_scan.json: {len(watchlist_scan_data)} \u53ea")

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
            atomic_write_text(report_path, report_md)

            # ── 趋势候选股资金交叉验证 ──
            # 从已缓存的全量排名中查询趋势候选股的主力净流入，补充写入 funding.json
            uptrend_codes = [
                r.code if hasattr(r, "code") else r.get("code", "")
                for r in trend_results
                if (
                    r.is_uptrend
                    if hasattr(r, "is_uptrend")
                    else r.get("is_uptrend", False)
                )
            ]
            uptrend_codes = [c for c in uptrend_codes if c]
            if uptrend_codes:
                trend_funding = fetch_funding_for_codes(uptrend_codes)
                funding_result = results.get("funding")
                if funding_result and funding_result[0] == "ok":
                    funding_data = funding_result[1]
                    if isinstance(funding_data, dict):
                        funding_data["trend_candidates_funding"] = trend_funding
                        funding_path = os.path.join(output_dir, "funding.json")
                        atomic_write_json(funding_path, funding_data)
                        _log(
                            f"  ✓ trend_candidates_funding: {len(trend_funding)} 只趋势股已补充资金数据"
                        )

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
                data = {"trade_date": data, "schema_version": _RAW_SCHEMA_VERSION}
            # 写入前精简数据
            if name.startswith("news_"):
                data = _slim_news(data)
            elif name == "trend_scan":
                data = _slim_trend_results(data)
            if isinstance(data, dict):
                data.setdefault("schema_version", _RAW_SCHEMA_VERSION)
                data.setdefault("source_run_id", run_id)
                data.setdefault("source_files", [])
            atomic_write_json(filepath, data)

        count = "-"
        if status == "ok":
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                if "top_inflow" in data:
                    count = data.get("sector_count", "-")
                elif "all_results" in data:
                    count = data.get("uptrend_count", len(data["all_results"]))
                elif name == "funding":
                    count = len(data.get("main_force_top20", []))

        summary["sources"][name] = {
            "status": status,
            "file": filename if status == "ok" else None,
            "count": count,
            "elapsed_sec": round(elapsed, 2),
            "error": data if status == "error" else None,
            "dq": _build_dq(name, data, status, now_ts),
        }

    total_elapsed = time.time() - t0
    summary["schema_version"] = _SUMMARY_SCHEMA_VERSION
    summary["source_run_id"] = run_id
    summary["source_files"] = sorted(
        [
            str(v["file"])
            for v in summary["sources"].values()
            if isinstance(v, dict) and isinstance(v.get("file"), str) and v.get("file")
        ]
    )
    summary["total_elapsed_sec"] = round(total_elapsed, 2)
    summary["ok_count"] = sum(
        1 for v in summary["sources"].values() if v["status"] == "ok"
    )
    summary["error_count"] = sum(
        1 for v in summary["sources"].values() if v["status"] == "error"
    )

    # 写 summary
    summary_path = os.path.join(output_dir, "collection_summary.json")
    atomic_write_json(summary_path, summary)

    run_id_path = os.path.join(output_dir, "run_id.json")
    atomic_write_json(
        run_id_path,
        {
            "schema_version": _RUN_ID_SCHEMA_VERSION,
            "run_id": run_id,
            "as_of_date": as_of_date,
            "strategy_version": strategy_version,
            "strategy_version_fallback": strategy_version_fallback,
            "source_run_id": run_id,
            "source_files": ["collection_summary.json"],
        },
    )

    return summary


# ── CLI 入口 ──────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="A股复盘数据采集")
    parser.add_argument("--output-dir", required=True, help="数据输出目录")
    parser.add_argument("--news-count", type=int, default=20, help="每类新闻条数")
    parser.add_argument("--taoguba-count", type=int, default=20, help="淘股吧帖子数")
    parser.add_argument("--no-scan-trends", action="store_true", help="跳过趋势扫描")
    parser.add_argument(
        "--popularity-max", type=int, default=1000, help="人气榜扫描上限(<=1000)"
    )

    args = parser.parse_args()

    _log(f"开始采集 -> {args.output_dir}")
    try:
        summary = collect(
            args.output_dir,
            args.news_count,
            args.taoguba_count,
            scan_trends=not args.no_scan_trends,
            popularity_max=args.popularity_max,

        )
    except RuntimeError as exc:
        _log(f"[ERROR] 采集中止：{exc}")
        sys.exit(1)

    _log(
        f"完成: {summary['ok_count']} 成功, {summary['error_count']} 失败, "
        f"耗时 {summary['total_elapsed_sec']}s"
    )

    if summary["error_count"] > 0:
        for name, info in summary["sources"].items():
            if info["status"] == "error":
                _log(f"  失败: {name} - {info['error']}")


if __name__ == "__main__":
    main()
