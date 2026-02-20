#!/usr/bin/env python3
"""独立风控校验脚本。

LLM 分析完毕输出候选股 JSON 后，由本脚本执行硬性规则校验。
代码执行 = 客观，不受 LLM "心软" 影响。

输入格式（JSON，从文件或 stdin）：
    {
      "total_capital": 100000,       # 总资金（元）
      "market_mode": "strong",       # strong / neutral / weak
      "account_mode": "normal",      # growth / normal / defensive / critical
      "candidates": [
        {
          "code": "000001",
          "name": "平安银行",
          "type": "trend",           # trend / theme
          "sector": "银行",          # 所属板块/题材
          "position": 15000          # 计划仓位（元）
        },
        ...
      ]
    }

输出格式（JSON，写到 stdout）：
    {
      "passed": true/false,
      "violations": [
        {"rule": "规则名", "detail": "具体说明", "severity": "warn/error"}
      ],
      "summary": "一句话总结"
    }

用法：
    python3 scripts/risk_check.py --input /tmp/.../candidates.json
    echo '<json>' | python3 scripts/risk_check.py
"""

import argparse
import json
import os
import sys
from typing import Any
from pathlib import Path

# ── 把 scripts 所在目录加入 sys.path，以便按包导入 ──
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from scripts.decision_logger import append_decision_log


# ── 风控规则 ─────────────────────────────────────────────────────

# 单只趋势股仓位上限（占总资金百分比）
TREND_SINGLE_LIMIT_PCT = 0.20
# 单只题材股仓位上限
THEME_SINGLE_LIMIT_PCT = 0.15
# 同一板块/题材候选股数量上限
SECTOR_COUNT_LIMIT = 3
# 同一板块/题材仓位占比上限
SECTOR_CAPITAL_LIMIT_PCT = 0.50
# 题材股总仓位上限（当市场为非题材驱动时）
THEME_TOTAL_LIMIT_PCT = 0.80
# 候选股数量上限
CANDIDATE_COUNT_MAX = 10
# 候选股数量下限（低于此数量提示信息）
CANDIDATE_COUNT_MIN = 3


def check(plan: dict) -> dict:
    """执行全量风控校验，返回结果 dict。"""
    violations: list[dict] = []

    total_capital: float = float(plan.get("total_capital", 0))
    candidates: list[dict] = plan.get("candidates", [])
    market_mode: str = plan.get("market_mode", "neutral")

    # ── 1. 候选股数量 ────────────────────────────────────────────
    n = len(candidates)
    if n > CANDIDATE_COUNT_MAX:
        violations.append({
            "rule": "候选股数量上限",
            "detail": f"候选股 {n} 只，超过建议上限 {CANDIDATE_COUNT_MAX} 只，建议精选",
            "severity": "warn",
        })
    if n < CANDIDATE_COUNT_MIN:
        violations.append({
            "rule": "候选股数量不足",
            "detail": f"候选股仅 {n} 只，建议至少 {CANDIDATE_COUNT_MIN} 只以分散风险",
            "severity": "warn",
        })

    if total_capital <= 0:
        # 没有总资金信息，跳过仓位比例检查
        passed = all(v["severity"] != "error" for v in violations)
        return _build_result(violations, passed)

    # ── 2. 单只仓位上限 ──────────────────────────────────────────
    for stock in candidates:
        code = stock.get("code", "?")
        name = stock.get("name", "?")
        position = float(stock.get("position", 0))
        stype = stock.get("type", "trend")

        if position <= 0:
            continue

        pct = position / total_capital
        limit = TREND_SINGLE_LIMIT_PCT if stype == "trend" else THEME_SINGLE_LIMIT_PCT

        if pct > limit:
            violations.append({
                "rule": "单只仓位超限",
                "detail": (
                    f"{code} {name} 计划仓位 {position:,.0f} 元 "
                    f"= {pct:.1%}，超过{'趋势股' if stype == 'trend' else '题材股'}上限 {limit:.0%}"
                ),
                "severity": "error",
            })

    # ── 3. 板块集中度（数量） ────────────────────────────────────
    sector_count: dict[str, int] = {}
    sector_capital: dict[str, float] = {}
    for stock in candidates:
        sector = stock.get("sector", "未知")
        sector_count[sector] = sector_count.get(sector, 0) + 1
        sector_capital[sector] = sector_capital.get(sector, 0.0) + float(stock.get("position", 0))

    for sector, count in sector_count.items():
        if count > SECTOR_COUNT_LIMIT:
            violations.append({
                "rule": "板块集中度（数量）",
                "detail": (
                    f"板块「{sector}」候选股 {count} 只，"
                    f"超过建议上限 {SECTOR_COUNT_LIMIT} 只"
                ),
                "severity": "warn",
            })

    # ── 4. 板块集中度（仓位比例） ────────────────────────────────
    for sector, cap in sector_capital.items():
        pct = cap / total_capital
        if pct > SECTOR_CAPITAL_LIMIT_PCT:
            violations.append({
                "rule": "板块集中度（仓位）",
                "detail": (
                    f"板块「{sector}」总计划仓位 {cap:,.0f} 元 = {pct:.1%}，"
                    f"超过上限 {SECTOR_CAPITAL_LIMIT_PCT:.0%}"
                ),
                "severity": "error",
            })

    # ── 5. 题材股总仓位（弱市/中性市场额外约束） ─────────────────
    if market_mode in ("weak", "neutral"):
        theme_total = sum(
            float(s.get("position", 0))
            for s in candidates
            if s.get("type") == "theme"
        )
        theme_pct = theme_total / total_capital
        if theme_pct > THEME_TOTAL_LIMIT_PCT:
            violations.append({
                "rule": "题材股总仓位过高",
                "detail": (
                    f"市场为{market_mode}，题材股总仓位 {theme_total:,.0f} 元 = {theme_pct:.1%}，"
                    f"超过当前市场风格下建议上限 {THEME_TOTAL_LIMIT_PCT:.0%}"
                ),
                "severity": "warn",
            })

    # ── 6. 账户防守/危机模式下的特殊约束 ────────────────────────
    account_mode: str = plan.get("account_mode", "normal")
    if account_mode in ("defensive", "critical"):
        theme_stocks = [s for s in candidates if s.get("type") == "theme"]
        if theme_stocks:
            names = "、".join(f"{s.get('code')} {s.get('name')}" for s in theme_stocks)
            violations.append({
                "rule": f"账户{account_mode}模式下不应新建题材仓",
                "detail": (
                    f"当前账户处于 {account_mode} 模式（回撤超标），"
                    f"以下题材股建议移除：{names}"
                ),
                "severity": "error" if account_mode == "critical" else "warn",
            })

    error_count = sum(1 for v in violations if v["severity"] == "error")
    passed = error_count == 0

    return _build_result(violations, passed)


def _build_result(violations: list[dict], passed: bool) -> dict:
    """构造输出结构。"""
    if passed and not violations:
        summary = "风控通过，无违规项。"
    elif passed:
        summary = f"风控通过（含 {len(violations)} 条警告，请人工复核）。"
    else:
        errors = [v for v in violations if v["severity"] == "error"]
        summary = f"风控不通过：{len(errors)} 条违规需修正。"

    return {"passed": passed, "violations": violations, "summary": summary}


# ── CLI 入口 ─────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="A股复盘风控校验")
    parser.add_argument("--input", "-i", help="候选股 JSON 文件路径（不填则从 stdin 读取）")
    parser.add_argument("--log-file", default="", help="可选：风控通过后写入 decision_log.jsonl")
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            plan: Any = json.load(f)
    else:
        plan = json.load(sys.stdin)

    result = check(plan)
    if result["passed"] and args.log_file and args.input:
        log_result = append_decision_log(Path(args.input), Path(args.log_file))
        if not log_result.get("ok"):
            result["violations"].append(
                {
                    "rule": "决策日志写入失败",
                    "detail": log_result.get("error", "unknown"),
                    "severity": "warn",
                }
            )
            result["summary"] = f"{result['summary']}（日志写入失败，已降级为仅报告）"
        else:
            result["decision_log"] = {
                "status": "ok",
                "run_id": log_result.get("run_id"),
                "log_file": log_result.get("log_file"),
            }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 有 error 级别违规时以非零状态退出，方便 shell 流程感知
    if not result["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
