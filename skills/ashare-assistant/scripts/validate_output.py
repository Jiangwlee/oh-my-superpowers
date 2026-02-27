#!/usr/bin/env python3
"""候选输出结构校验器。"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ALLOWED_MARKET_REGIME = {"strong", "neutral", "weak"}
_ALLOWED_ACTION = {"buy", "hold", "sell", "watch"}


def _is_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def _is_run_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d{8}-[A-Za-z0-9_.-]+-\d{6}", value))


def _append_error(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_candidate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验 schema_v1 核心字段。"""
    errors: list[str] = []
    warnings: list[str] = []

    run_id = payload.get("run_id")
    _append_error(errors, isinstance(run_id, str) and _is_run_id(run_id), "run_id 缺失或格式错误")

    as_of_date = payload.get("as_of_date")
    _append_error(
        errors,
        isinstance(as_of_date, str) and _is_date(as_of_date),
        "as_of_date 缺失或不是 YYYY-MM-DD",
    )

    market = payload.get("market") if isinstance(payload.get("market"), dict) else {}
    regime = market.get("regime")
    _append_error(
        errors,
        isinstance(regime, str) and regime in _ALLOWED_MARKET_REGIME,
        "market.regime 缺失或枚举值无效",
    )

    funding = payload.get("funding") if isinstance(payload.get("funding"), dict) else {}
    _append_error(
        errors,
        isinstance(funding.get("data_degraded"), bool),
        "funding.data_degraded 缺失或不是布尔值",
    )

    candidates = payload.get("candidates")
    _append_error(errors, isinstance(candidates, list) and len(candidates) > 0, "candidates 缺失或为空")

    if isinstance(candidates, list):
        for idx, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                errors.append(f"candidates[{idx}] 不是对象")
                continue
            for field in ("code", "name", "score", "action", "thesis_short", "risk_note"):
                if field not in candidate:
                    errors.append(f"candidates[{idx}].{field} 缺失")
            action = candidate.get("action")
            if not isinstance(action, str) or action not in _ALLOWED_ACTION:
                errors.append(f"candidates[{idx}].action 枚举值无效")
            thesis_short = candidate.get("thesis_short")
            risk_note = candidate.get("risk_note")
            if isinstance(thesis_short, str) and len(thesis_short) > 30:
                warnings.append(f"candidates[{idx}].thesis_short 超过 30 字")
            if isinstance(risk_note, str) and len(risk_note) > 30:
                warnings.append(f"candidates[{idx}].risk_note 超过 30 字")

    risk_flags = payload.get("risk_flags") if isinstance(payload.get("risk_flags"), dict) else {}
    for key in ("data_degraded", "output_schema_invalid", "strategy_version_fallback"):
        _append_error(
            errors,
            isinstance(risk_flags.get(key), bool),
            f"risk_flags.{key} 缺失或不是布尔值",
        )

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def run_self_test() -> dict[str, Any]:
    """内置冒烟测试。"""
    sample = {
        "run_id": "20260220-v1.0-103000",
        "as_of_date": "2026-02-20",
        "market": {"regime": "strong"},
        "funding": {"data_degraded": False},
        "candidates": [
            {
                "code": "000001",
                "name": "平安银行",
                "score": 4.0,
                "action": "buy",
                "thesis_short": "趋势延续",
                "risk_note": "分歧回撤",
            }
        ],
        "risk_flags": {
            "data_degraded": False,
            "output_schema_invalid": False,
            "strategy_version_fallback": False,
        },
    }
    return validate_candidate_payload(sample)


def main() -> None:
    parser = argparse.ArgumentParser(description="校验 candidates.json 是否满足 schema_v1 核心约束")
    parser.add_argument("--input", default="", help="输入 JSON 文件")
    parser.add_argument("--test", action="store_true", help="运行内置自测")
    args = parser.parse_args()

    if args.test:
        result = run_self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["ok"] else 1)

    if not args.input:
        print(json.dumps({"ok": False, "errors": ["缺少 --input"], "warnings": []}, ensure_ascii=False))
        raise SystemExit(1)

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as exc:
        logger.exception("读取输入失败: %s", exc)
        print(json.dumps({"ok": False, "errors": [f"读取失败: {exc}"], "warnings": []},
                         ensure_ascii=False))
        raise SystemExit(1)

    if not isinstance(payload, dict):
        print(json.dumps({"ok": False, "errors": ["顶层必须是 JSON 对象"], "warnings": []}, ensure_ascii=False))
        raise SystemExit(1)

    result = validate_candidate_payload(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
