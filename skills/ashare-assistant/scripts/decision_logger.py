#!/usr/bin/env python3
"""写入交易决策日志（decision_log.jsonl）。"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ashare_data.core.config import DECISION_LOG

logger = logging.getLogger(__name__)


def _build_record(payload: dict[str, Any]) -> dict[str, Any]:
    market = payload.get("market") if isinstance(payload.get("market"), dict) else {}
    risk_flags = payload.get("risk_flags") if isinstance(payload.get("risk_flags"), dict) else {}

    compact_candidates: list[dict[str, Any]] = []
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        compact_candidates.append(
            {
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "score": item.get("score", 0),
                "action": item.get("action", "watch"),
            }
        )

    return {
        "run_id": payload.get("run_id", ""),
        "as_of_date": payload.get("as_of_date", ""),
        "market_regime": market.get("regime", "neutral"),
        "candidates": compact_candidates,
        "risk_flags": risk_flags,
        "outcome": {
            "t1": None,
            "t5": None,
            "benchmark_t1": None,
            "benchmark_t5": None,
            "excess_t1": None,
            "excess_t5": None,
            "written_at": None,
        },
        "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def append_decision_log(input_path: Path, log_file: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"ok": False, "error": "输入不是 JSON 对象"}

    risk_flags = payload.get("risk_flags") if isinstance(payload.get("risk_flags"), dict) else {}
    if payload.get("run_failed") is True or risk_flags.get("output_schema_invalid") is True:
        return {"ok": False, "error": "schema 无效或 run_failed，跳过 decision_log"}

    record = _build_record(payload)
    if not record["run_id"] or not record["as_of_date"]:
        return {"ok": False, "error": "run_id/as_of_date 缺失"}

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"ok": True, "log_file": str(log_file), "run_id": record["run_id"]}


def run_self_test() -> dict[str, Any]:
    return {"ok": True, "message": "decision_logger self-test passed"}


def main() -> None:
    parser = argparse.ArgumentParser(description="将 candidates.json 追加到 decision_log.jsonl")
    parser.add_argument("--input", default="", help="输入 candidates.json")
    parser.add_argument("--log-file", default=str(DECISION_LOG), help="输出日志路径")
    parser.add_argument("--test", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.test:
        print(json.dumps(run_self_test(), ensure_ascii=False, indent=2))
        raise SystemExit(0)

    if not args.input:
        print(json.dumps({"ok": False, "error": "缺少 --input"}, ensure_ascii=False))
        raise SystemExit(1)

    try:
        result = append_decision_log(Path(args.input), Path(args.log_file))
    except Exception as exc:
        logger.exception("decision_logger 失败: %s", exc)
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
