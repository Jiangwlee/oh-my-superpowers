#!/usr/bin/env python3
"""回填 T+1/T+5 结果并输出反馈摘要。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.fetchers.trend_scanner import fetch_jrj_daily_kline


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _ymd(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def _pick_close_for_date(kline: list[dict[str, Any]], date_value: datetime) -> float | None:
    target = int(date_value.strftime("%Y%m%d"))
    for bar in kline:
        t_val = bar.get("time")
        if isinstance(t_val, int) and t_val == target:
            close = bar.get("close")
            return float(close) if close is not None else None
    return None


def _first_after_date(kline: list[dict[str, Any]], date_value: datetime) -> tuple[int, float] | None:
    target = int(date_value.strftime("%Y%m%d"))
    rows: list[tuple[int, float]] = []
    for bar in kline:
        t_val = bar.get("time")
        close = bar.get("close")
        if isinstance(t_val, int) and isinstance(close, (int, float)) and t_val > target:
            rows.append((t_val, float(close)))
    if not rows:
        return None
    rows.sort(key=lambda item: item[0])
    return rows[0]


def fetch_candidate_t1_return(code: str, as_of_date: str) -> float | None:
    base_date = _parse_date(as_of_date)
    if base_date is None:
        return None
    kline = fetch_jrj_daily_kline(code, range_num=30)
    base_close = _pick_close_for_date(kline, base_date)
    next_row = _first_after_date(kline, base_date)
    if base_close is None or next_row is None or base_close == 0:
        return None
    return round((next_row[1] - base_close) / base_close * 100.0, 3)


def fetch_benchmark_t1_return(as_of_date: str) -> float | None:
    # 沪深300近似使用指数代码 000300
    return fetch_candidate_t1_return("000300", as_of_date)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_feedback(feedback_file: Path, rows: list[dict[str, Any]], today: datetime) -> None:
    buy_rows = [row for row in rows if row.get("candidates") and row["candidates"][0].get("action") == "buy"]
    t1_values = [
        row.get("outcome", {}).get("t1")
        for row in buy_rows
        if isinstance(row.get("outcome", {}).get("t1"), (int, float))
    ]
    benchmark_values = [
        row.get("outcome", {}).get("benchmark_t1")
        for row in buy_rows
        if isinstance(row.get("outcome", {}).get("benchmark_t1"), (int, float))
    ]
    if not t1_values:
        return

    win_rate = sum(1 for item in t1_values if item > 0) / len(t1_values) * 100.0
    avg_t1 = sum(t1_values) / len(t1_values)
    avg_benchmark = sum(benchmark_values) / len(benchmark_values) if benchmark_values else 0.0

    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    section = (
        f"\n## 诊断报告 - {_ymd(today - timedelta(days=7))} ~ {_ymd(today)}\n"
        f"- 样本数（buy）：{len(t1_values)}\n"
        f"- 次日胜率（T+1）：{win_rate:.1f}%\n"
        f"- 平均收益（T+1）：{avg_t1:.3f}%\n"
        f"- 沪深300平均（T+1）：{avg_benchmark:.3f}%\n"
        f"- 平均超额（T+1）：{(avg_t1 - avg_benchmark):.3f}%\n"
    )
    with feedback_file.open("a", encoding="utf-8") as handle:
        handle.write(section)


def process_diagnose(
    *,
    log_file: Path,
    feedback_file: Path,
    dry_run: bool = False,
    today: str | None = None,
) -> dict[str, Any]:
    today_dt = _parse_date(today) if today else datetime.now()
    if today_dt is None:
        return {"ok": False, "error": "today 参数格式错误"}

    rows = _load_jsonl(log_file)
    updated = 0

    for row in rows:
        as_of_date = row.get("as_of_date")
        run_date = _parse_date(as_of_date) if isinstance(as_of_date, str) else None
        if run_date is None:
            continue

        outcome = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}
        if outcome.get("t1") is not None:
            continue
        if run_date > (today_dt - timedelta(days=1)):
            continue

        candidates = row.get("candidates") if isinstance(row.get("candidates"), list) else []
        buy_codes = [
            item.get("code")
            for item in candidates
            if isinstance(item, dict) and item.get("action") == "buy" and isinstance(item.get("code"), str)
        ]
        if not buy_codes:
            continue

        values: list[float] = []
        for code in buy_codes:
            ret = fetch_candidate_t1_return(code, as_of_date)
            if isinstance(ret, (int, float)):
                values.append(float(ret))

        if not values:
            continue

        benchmark = fetch_benchmark_t1_return(as_of_date)
        mean_t1 = round(sum(values) / len(values), 3)
        benchmark_val = round(float(benchmark), 3) if isinstance(benchmark, (int, float)) else None
        excess = round(mean_t1 - benchmark_val, 3) if benchmark_val is not None else None

        outcome["t1"] = mean_t1
        outcome["benchmark_t1"] = benchmark_val
        outcome["excess_t1"] = excess
        outcome["written_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row["outcome"] = outcome
        updated += 1

    if not dry_run:
        _write_jsonl(log_file, rows)
        if updated > 0:
            _append_feedback(feedback_file, rows, today_dt)

    return {"ok": True, "updated": updated, "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser(description="回填 decision_log 的 T+1/T+5 结果（当前实现 T+1）")
    parser.add_argument("--log-file", default=".memory/decision_log.jsonl", help="决策日志路径")
    parser.add_argument("--feedback-file", default="evolution/feedback.md", help="反馈文件路径")
    parser.add_argument("--today", default="", help="覆盖当前日期 YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="只演算，不写回")
    args = parser.parse_args()

    result = process_diagnose(
        log_file=Path(args.log_file),
        feedback_file=Path(args.feedback_file),
        dry_run=args.dry_run,
        today=args.today or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
