#!/usr/bin/env python3
"""回填 T+1/T+5 结果并输出反馈摘要。

沪深300 基准使用 JRJ K线接口（securityId=1000300），
不依赖 _to_jrj_security_id 的股票映射逻辑（该函数对指数代码映射有误）。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ashare_data.core.config import ASHARE_HOME, DECISION_LOG
from ashare_data.fetchers.trend_scanner import fetch_jrj_daily_kline
from ashare_data.core.http_client import http_json
from ashare_data.core.utils import atomic_write_text

FEEDBACK_FILE = ASHARE_HOME / "evolution" / "feedback.md"
_OUTCOME_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# 日期工具
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _ymd(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# K线工具
# ---------------------------------------------------------------------------

def _pick_close_for_date(kline: list[dict[str, Any]], date_value: datetime) -> float | None:
    target = int(date_value.strftime("%Y%m%d"))
    for bar in kline:
        t_val = bar.get("time")
        if isinstance(t_val, int) and t_val == target:
            close = bar.get("close")
            return float(close) if close is not None else None
    return None


def _nth_after_date(
    kline: list[dict[str, Any]], date_value: datetime, n: int
) -> tuple[int, float] | None:
    """返回 date_value 之后第 n 个交易日的 (date_int, close)。"""
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
    if len(rows) < n:
        return None
    return rows[n - 1]


# ---------------------------------------------------------------------------
# 个股涨跌幅
# ---------------------------------------------------------------------------

def _pct_change(base: float | None, target: float | None) -> float | None:
    if base is None or target is None or base == 0:
        return None
    return round((target - base) / base * 100.0, 3)


def fetch_candidate_tn_return(code: str, as_of_date: str, n: int) -> float | None:
    """获取 code 在 as_of_date 后第 n 个交易日的涨跌幅（%）。"""
    base_date = _parse_date(as_of_date)
    if base_date is None:
        return None
    kline = fetch_jrj_daily_kline(code, range_num=max(30, n + 20))
    base_close = _pick_close_for_date(kline, base_date)
    nth_row = _nth_after_date(kline, base_date, n)
    if nth_row is None:
        return None
    return _pct_change(base_close, nth_row[1])


# ---------------------------------------------------------------------------
# 沪深300 基准 — 直接使用 securityId=1000300，绕过 _to_jrj_security_id 映射
# ---------------------------------------------------------------------------

def _fetch_hs300_kline(range_num: int = 40) -> list[dict[str, Any]]:
    """获取沪深300 日K线（JRJ 接口，securityId 固定为 1000300）。

    _to_jrj_security_id("000300") → "2000300"（错误），需直接构造 URL。
    实测 securityId=1000300 可正常返回数据，价格单位与个股相同（均为 0.0001 元/点）。
    """
    today_str = datetime.now().strftime("%Y%m%d")
    url = "https://gateway.jrj.com/quot-kline?" + urlencode({
        "format": "json",
        "securityId": "1000300",
        "type": "day",
        "direction": "left",
        "range.num": str(range_num),
        "range.begin": today_str,
    })
    try:
        data = http_json(url)
        kline_raw = data.get("data", {}).get("kline", []) or []
        out: list[dict[str, Any]] = []
        for item in kline_raw:
            t = item.get("nTime")
            cp = item.get("nLastPx")
            if t is not None and cp is not None:
                out.append({"time": int(t), "close": float(cp)})
        out.sort(key=lambda x: x["time"])
        return out
    except Exception:
        return []


def fetch_benchmark_tn_return(as_of_date: str, n: int) -> float | None:
    """获取沪深300 在 as_of_date 后第 n 个交易日的涨跌幅（%）。"""
    base_date = _parse_date(as_of_date)
    if base_date is None:
        return None
    kline = _fetch_hs300_kline(range_num=max(30, n + 20))
    base_close = _pick_close_for_date(kline, base_date)
    nth_row = _nth_after_date(kline, base_date, n)
    if nth_row is None:
        return None
    return _pct_change(base_close, nth_row[1])


# ---------------------------------------------------------------------------
# JSONL 读写
# ---------------------------------------------------------------------------

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
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    atomic_write_text(path, payload)


# ---------------------------------------------------------------------------
# feedback.md 生成
# ---------------------------------------------------------------------------

def _append_feedback(feedback_file: Path, rows: list[dict[str, Any]], today: datetime) -> None:
    """追加诊断报告到 feedback.md。

    统计口径：以个股为单位，仅统计 outcome.t1/t5 不为 null 的记录。
    即 process_diagnose 中对所有 action=buy 个股求平均后写入 outcome 的行。
    """
    t1_values = [
        row["outcome"]["t1"]
        for row in rows
        if isinstance(row.get("outcome", {}).get("t1"), (int, float))
    ]
    benchmark_t1_values = [
        row["outcome"]["benchmark_t1"]
        for row in rows
        if isinstance(row.get("outcome", {}).get("benchmark_t1"), (int, float))
    ]
    t5_values = [
        row["outcome"]["t5"]
        for row in rows
        if isinstance(row.get("outcome", {}).get("t5"), (int, float))
    ]

    if not t1_values:
        return

    win_rate_t1 = sum(1 for v in t1_values if v > 0) / len(t1_values) * 100.0
    avg_t1 = sum(t1_values) / len(t1_values)
    avg_bm_t1 = sum(benchmark_t1_values) / len(benchmark_t1_values) if benchmark_t1_values else 0.0

    t5_section = ""
    if t5_values:
        win_rate_t5 = sum(1 for v in t5_values if v > 0) / len(t5_values) * 100.0
        avg_t5 = sum(t5_values) / len(t5_values)
        t5_section = (
            f"- T+5 样本数：{len(t5_values)}\n"
            f"- T+5 胜率：{win_rate_t5:.1f}%\n"
            f"- T+5 平均收益：{avg_t5:.3f}%\n"
        )

    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    section = (
        f"\n## 诊断报告 - {_ymd(today - timedelta(days=7))} ~ {_ymd(today)}\n"
        f"- T+1 样本数（含 buy 候选的运行次数）：{len(t1_values)}\n"
        f"- T+1 胜率：{win_rate_t1:.1f}%\n"
        f"- T+1 平均收益：{avg_t1:.3f}%\n"
        f"- T+1 沪深300平均：{avg_bm_t1:.3f}%\n"
        f"- T+1 平均超额：{(avg_t1 - avg_bm_t1):.3f}%\n"
        + t5_section
    )
    with feedback_file.open("a", encoding="utf-8") as handle:
        handle.write(section)


# ---------------------------------------------------------------------------
# 主处理逻辑
# ---------------------------------------------------------------------------

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
    updated_t1 = 0
    updated_t5 = 0

    for row in rows:
        as_of_date = row.get("as_of_date")
        run_date = _parse_date(as_of_date) if isinstance(as_of_date, str) else None
        if run_date is None:
            continue

        outcome = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}

        candidates = row.get("candidates") if isinstance(row.get("candidates"), list) else []
        buy_codes = [
            item.get("code")
            for item in candidates
            if isinstance(item, dict) and item.get("action") == "buy" and isinstance(item.get("code"), str)
        ]
        if not buy_codes:
            continue

        # --- T+1 回填 ---
        if outcome.get("t1") is None and run_date <= (today_dt - timedelta(days=1)):
            values: list[float] = []
            for code in buy_codes:
                ret = fetch_candidate_tn_return(code, as_of_date, n=1)
                if isinstance(ret, (int, float)):
                    values.append(float(ret))

            if values:
                benchmark = fetch_benchmark_tn_return(as_of_date, n=1)
                mean_t1 = round(sum(values) / len(values), 3)
                bm_val = round(float(benchmark), 3) if isinstance(benchmark, (int, float)) else None
                excess = round(mean_t1 - bm_val, 3) if bm_val is not None else None

                outcome["t1"] = mean_t1
                outcome["benchmark_t1"] = bm_val
                outcome["excess_t1"] = excess
                outcome["schema_version"] = _OUTCOME_SCHEMA_VERSION
                outcome["written_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                row["outcome"] = outcome
                updated_t1 += 1

        # --- T+5 回填（约需5个交易日 ≈ 7个自然日） ---
        if outcome.get("t5") is None and run_date <= (today_dt - timedelta(days=7)):
            values5: list[float] = []
            for code in buy_codes:
                ret5 = fetch_candidate_tn_return(code, as_of_date, n=5)
                if isinstance(ret5, (int, float)):
                    values5.append(float(ret5))

            if values5:
                benchmark5 = fetch_benchmark_tn_return(as_of_date, n=5)
                mean_t5 = round(sum(values5) / len(values5), 3)
                bm_val5 = round(float(benchmark5), 3) if isinstance(benchmark5, (int, float)) else None
                excess5 = round(mean_t5 - bm_val5, 3) if bm_val5 is not None else None

                outcome["t5"] = mean_t5
                outcome["benchmark_t5"] = bm_val5
                outcome["excess_t5"] = excess5
                outcome["schema_version"] = _OUTCOME_SCHEMA_VERSION
                row["outcome"] = outcome
                updated_t5 += 1

    if not dry_run:
        _write_jsonl(log_file, rows)
        if updated_t1 > 0 or updated_t5 > 0:
            _append_feedback(feedback_file, rows, today_dt)

    return {"ok": True, "updated_t1": updated_t1, "updated_t5": updated_t5, "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser(description="回填 decision_log 的 T+1/T+5 结果")
    parser.add_argument("--log-file", default=str(DECISION_LOG), help="决策日志路径")
    parser.add_argument("--feedback-file", default=str(FEEDBACK_FILE), help="反馈文件路径")
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
