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
    python3 -m scripts.risk_check --input /tmp/.../candidates.json
    python3 -m scripts.risk_check --input /tmp/.../candidates.json --strategy strategy/active.yaml
    echo '<json>' | python3 -m scripts.risk_check
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from scripts.decision_logger import append_decision_log

logger = logging.getLogger(__name__)

# ── 风控参数默认值（与 strategy/default.yaml risk_limits 保持一致）────────────
_DEFAULT_LIMITS = {
    "trend_single_limit": 0.20,
    "theme_single_limit": 0.15,
    "sector_count_limit": 3,
    "sector_capital_limit": 0.50,
    "theme_total_limit": 0.80,
    "candidate_count_max": 10,
    "candidate_count_min": 3,
}


def _load_limits(strategy_path: str) -> dict[str, Any]:
    """从策略文件读取 risk_limits，缺失时使用默认值。"""
    limits = dict(_DEFAULT_LIMITS)
    try:
        import yaml  # type: ignore
        with open(strategy_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        limits.update(data.get("risk_limits", {}))
    except Exception as exc:
        logger.warning("无法加载策略文件 %s，使用默认风控参数: %s", strategy_path, exc)
    return limits


def check(plan: dict, limits: dict[str, Any] | None = None) -> dict:
    """执行全量风控校验，返回结果 dict。"""
    if limits is None:
        limits = _DEFAULT_LIMITS

    violations: list[dict] = []

    total_capital: float = float(plan.get("total_capital", 0))
    candidates: list[dict] = plan.get("candidates", [])
    market_mode: str = plan.get("market_mode", "neutral")

    candidate_count_max: int = int(limits["candidate_count_max"])
    candidate_count_min: int = int(limits["candidate_count_min"])

    # ── 1. 候选股数量 ────────────────────────────────────────────
    n = len(candidates)
    if n > candidate_count_max:
        violations.append({
            "rule": "候选股数量上限",
            "detail": f"候选股 {n} 只，超过建议上限 {candidate_count_max} 只，建议精选",
            "severity": "warn",
        })
    if n < candidate_count_min:
        violations.append({
            "rule": "候选股数量不足",
            "detail": f"候选股仅 {n} 只，建议至少 {candidate_count_min} 只以分散风险",
            "severity": "warn",
        })

    if total_capital <= 0:
        # 没有总资金信息，跳过仓位比例检查
        passed = all(v["severity"] != "error" for v in violations)
        return _build_result(violations, passed)

    trend_single_limit: float = float(limits["trend_single_limit"])
    theme_single_limit: float = float(limits["theme_single_limit"])
    sector_count_limit: int = int(limits["sector_count_limit"])
    sector_capital_limit: float = float(limits["sector_capital_limit"])
    theme_total_limit: float = float(limits["theme_total_limit"])

    # ── 2. 单只仓位上限 ──────────────────────────────────────────
    for stock in candidates:
        code = stock.get("code", "?")
        name = stock.get("name", "?")
        position = float(stock.get("position", 0))
        stype = stock.get("type", "trend")

        if position <= 0:
            continue

        pct = position / total_capital
        limit = trend_single_limit if stype == "trend" else theme_single_limit

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
        if count > sector_count_limit:
            violations.append({
                "rule": "板块集中度（数量）",
                "detail": (
                    f"板块「{sector}」候选股 {count} 只，"
                    f"超过建议上限 {sector_count_limit} 只"
                ),
                "severity": "warn",
            })

    # ── 4. 板块集中度（仓位比例） ────────────────────────────────
    for sector, cap in sector_capital.items():
        pct = cap / total_capital
        if pct > sector_capital_limit:
            violations.append({
                "rule": "板块集中度（仓位）",
                "detail": (
                    f"板块「{sector}」总计划仓位 {cap:,.0f} 元 = {pct:.1%}，"
                    f"超过上限 {sector_capital_limit:.0%}"
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
        if theme_pct > theme_total_limit:
            violations.append({
                "rule": "题材股总仓位过高",
                "detail": (
                    f"市场为{market_mode}，题材股总仓位 {theme_total:,.0f} 元 = {theme_pct:.1%}，"
                    f"超过当前市场风格下建议上限 {theme_total_limit:.0%}"
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
    parser.add_argument(
        "--strategy", default="strategy/active.yaml",
        help="策略文件路径（含 risk_limits 段），默认 strategy/active.yaml"
    )
    args = parser.parse_args()

    limits = _load_limits(args.strategy)

    try:
        if args.input:
            with open(args.input, encoding="utf-8") as f:
                plan: Any = json.load(f)
        else:
            plan = json.load(sys.stdin)
    except Exception as exc:
        logger.exception("读取输入失败: %s", exc)
        print(json.dumps({"passed": False, "violations": [], "summary": f"输入读取失败: {exc}"},
                         ensure_ascii=False))
        sys.exit(1)

    result = check(plan, limits)
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
