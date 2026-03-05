"""数据治理工具：retention、血缘、质量门禁。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ashare_data.core.config import ASHARE_HOME, DATA_DIR, DECISION_LOG
from ashare_data.core.utils import atomic_write_text

_CN_FORMAT = "%Y-%m-%d"
_KEEP_SIGNAL_FILES = {"watchlist_signals.json", "post_close_decisions.json"}


def load_latest_run_id() -> str:
    if not DATA_DIR.exists():
        return ""
    dated_dirs = [p for p in DATA_DIR.iterdir() if p.is_dir()]
    dated_dirs.sort(key=lambda p: p.name, reverse=True)
    for d in dated_dirs:
        run_id_path = d / "raw" / "run_id.json"
        if not run_id_path.exists():
            continue
        try:
            payload = json.loads(run_id_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        run_id = payload.get("run_id")
        if isinstance(run_id, str) and run_id:
            return run_id
    return ""


def apply_retention_policy(
    *,
    data_days: int = 45,
    signals_days: int = 14,
    decision_log_days: int = 365,
) -> dict[str, Any]:
    now = datetime.now()
    data_cutoff = now - timedelta(days=max(0, data_days))
    signals_cutoff = now - timedelta(days=max(0, signals_days))
    decision_cutoff = now - timedelta(days=max(0, decision_log_days))

    removed_data_dirs: list[str] = []
    if DATA_DIR.exists():
        for item in DATA_DIR.iterdir():
            if not item.is_dir():
                continue
            try:
                folder_date = datetime.strptime(item.name, _CN_FORMAT)
            except ValueError:
                continue
            if folder_date >= data_cutoff:
                continue
            for child in sorted(item.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    child.rmdir()
            item.rmdir()
            removed_data_dirs.append(item.name)

    removed_signal_files: list[str] = []
    signals_dir = ASHARE_HOME / "signals"
    if signals_dir.exists():
        for path in signals_dir.glob("*.json"):
            if path.name in _KEEP_SIGNAL_FILES:
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified >= signals_cutoff:
                continue
            path.unlink(missing_ok=True)
            removed_signal_files.append(path.name)

    decision_log_pruned = 0
    if DECISION_LOG.exists():
        kept_lines: list[str] = []
        for line in DECISION_LOG.read_text(encoding="utf-8").splitlines():
            row = None
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                kept_lines.append(line)
                continue
            if not isinstance(row, dict):
                kept_lines.append(line)
                continue
            as_of_date = row.get("as_of_date")
            if not isinstance(as_of_date, str):
                kept_lines.append(line)
                continue
            try:
                row_date = datetime.strptime(as_of_date, _CN_FORMAT)
            except ValueError:
                kept_lines.append(line)
                continue
            if row_date < decision_cutoff:
                decision_log_pruned += 1
                continue
            kept_lines.append(line)
        atomic_write_text(DECISION_LOG, "\n".join(kept_lines) + ("\n" if kept_lines else ""))

    return {
        "removed_data_dirs": removed_data_dirs,
        "removed_signal_files": removed_signal_files,
        "decision_log_pruned": decision_log_pruned,
    }


def evaluate_degraded(summary_sources: dict[str, Any], error_count: int, filter_errors: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if error_count > 0:
        reasons.append(f"collect_error_count={error_count}")
    if filter_errors > 0:
        reasons.append(f"filter_error_count={filter_errors}")

    critical_sources = {"news_headline", "funding", "trade_date", "trend_scan"}
    for name in critical_sources:
        src = summary_sources.get(name)
        if not isinstance(src, dict):
            reasons.append(f"missing_source={name}")
            continue
        if src.get("status") != "ok":
            reasons.append(f"source_status_{name}={src.get('status')}")
            continue
        dq = src.get("dq")
        if isinstance(dq, dict) and dq.get("is_empty") is True:
            reasons.append(f"source_empty={name}")
    return (len(reasons) > 0, reasons)
