#!/usr/bin/env python3
"""批量执行第3.5步个股深度分析（并行 + 超时 + 耗时日志）。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILL_ROOT = _SCRIPTS_DIR.parent


@dataclass
class CommandResult:
    """命令执行结果。"""

    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str], float], CommandResult]


def normalize_full_code(code: str) -> str:
    """将 6 位股票代码转换为 `szXXXXXX` 或 `shXXXXXX`。"""
    raw = code.strip().lower()
    if raw.startswith(("sz", "sh")) and len(raw) == 8:
        return raw

    six = "".join(ch for ch in raw if ch.isdigit())
    if len(six) != 6:
        return raw

    prefix = "sh" if six.startswith(("5", "6", "9")) else "sz"
    return f"{prefix}{six}"


def _default_command_runner(cmd: list[str], timeout_sec: float) -> CommandResult:
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=max(1.0, timeout_sec),
        check=False,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _build_stock_commands(
    *,
    skill_root: Path,
    output_dir: Path,
    code: str,
    full_code: str,
    post_limit: int,
    detail_limit: int,
    notice_days: int,
    quotes_count: int,
    zh_page: int,
    zh_count: int,
) -> list[tuple[str, list[str]]]:
    em_raw = output_dir / f"dr_{code}_em.json"
    tgb_raw = output_dir / f"dr_{code}_tgb.json"
    compact = output_dir / f"dr_{code}_compact.json"
    scripts_dir = skill_root / "scripts"

    return [
        (
            "eastmoney",
            [
                sys.executable,
                str(scripts_dir / "collect_eastmoney_guba.py"),
                "--code",
                code,
                "--output",
                str(em_raw),
                "--post-limit",
                str(post_limit),
                "--detail-limit",
                str(detail_limit),
                "--notice-days",
                str(notice_days),
            ],
        ),
        (
            "taoguba",
            [
                sys.executable,
                str(scripts_dir / "collect_taoguba_stock.py"),
                "--full-code",
                full_code,
                "--output",
                str(tgb_raw),
                "--quotes-count",
                str(quotes_count),
                "--zh-page",
                str(zh_page),
                "--zh-count",
                str(zh_count),
            ],
        ),
        (
            "compact",
            [
                sys.executable,
                str(scripts_dir / "summarize_stock_brief.py"),
                "--code",
                code,
                "--em-raw",
                str(em_raw),
                "--tgb-raw",
                str(tgb_raw),
                "--output",
                str(compact),
                "--compact-only",
            ],
        ),
    ]


def run_stock_deep_research(
    *,
    code: str,
    output_dir: Path,
    skill_root: Path,
    per_stock_timeout_sec: float,
    command_runner: CommandRunner | None = None,
    post_limit: int = 36,
    detail_limit: int = 5,
    notice_days: int = 3,
    quotes_count: int = 8,
    zh_page: int = 1,
    zh_count: int = 20,
) -> dict[str, Any]:
    """执行单只股票的深度分析脚本链路。"""
    runner = command_runner or _default_command_runner
    stock_start = time.monotonic()
    full_code = normalize_full_code(code)
    steps: list[dict[str, Any]] = []

    commands = _build_stock_commands(
        skill_root=skill_root,
        output_dir=output_dir,
        code=code,
        full_code=full_code,
        post_limit=post_limit,
        detail_limit=detail_limit,
        notice_days=notice_days,
        quotes_count=quotes_count,
        zh_page=zh_page,
        zh_count=zh_count,
    )

    status = "ok"
    error = ""
    for step_name, cmd in commands:
        elapsed_before = time.monotonic() - stock_start
        remain = per_stock_timeout_sec - elapsed_before
        if remain <= 0:
            status = "timeout"
            error = "per_stock_timeout_exceeded"
            break

        step_start = time.monotonic()
        step_result: dict[str, Any] = {
            "name": step_name,
            "cmd": cmd,
            "status": "ok",
            "elapsed_sec": 0.0,
            "stderr": "",
        }
        try:
            result = runner(cmd, remain)
            step_elapsed = time.monotonic() - step_start
            step_result["elapsed_sec"] = round(step_elapsed, 3)
            step_result["stderr"] = result.stderr
            if result.returncode != 0:
                step_result["status"] = "error"
                status = "error"
                error = f"{step_name}_failed"
                steps.append(step_result)
                break
            steps.append(step_result)
        except TimeoutError:
            step_elapsed = time.monotonic() - step_start
            step_result["elapsed_sec"] = round(step_elapsed, 3)
            step_result["status"] = "timeout"
            step_result["stderr"] = "step_timeout"
            status = "timeout"
            error = f"{step_name}_timeout"
            steps.append(step_result)
            break

    return {
        "code": code,
        "full_code": full_code,
        "status": status,
        "error": error or None,
        "elapsed_sec": round(time.monotonic() - stock_start, 3),
        "steps": steps,
    }


def write_timing_report(*, output_dir: Path, rows: list[dict[str, Any]]) -> Path:
    """写入批量执行耗时报告。"""
    summary = {
        "total": len(rows),
        "ok": sum(1 for row in rows if row.get("status") == "ok"),
        "error": sum(1 for row in rows if row.get("status") == "error"),
        "timeout": sum(1 for row in rows if row.get("status") == "timeout"),
        "elapsed_sec_sum": round(sum(float(row.get("elapsed_sec", 0.0)) for row in rows), 3),
    }
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "stocks": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "dr_timing.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def run_batch_deep_research(
    *,
    codes: list[str],
    output_dir: Path,
    skill_root: Path,
    max_workers: int,
    per_stock_timeout_sec: float,
    total_timeout_sec: float,
    post_limit: int,
    detail_limit: int,
    notice_days: int,
    quotes_count: int,
    zh_page: int,
    zh_count: int,
) -> dict[str, Any]:
    """并行执行多只股票深度分析。"""
    start = time.monotonic()
    unique_codes = []
    seen: set[str] = set()
    for code in codes:
        normalized = "".join(ch for ch in code if ch.isdigit())
        if len(normalized) == 6 and normalized not in seen:
            seen.add(normalized)
            unique_codes.append(normalized)

    if not unique_codes:
        return {"ok": False, "error": "no_valid_codes", "rows": []}

    rows: list[dict[str, Any]] = []
    max_pool = max(1, min(max_workers, len(unique_codes)))
    deadline = start + total_timeout_sec if total_timeout_sec > 0 else None

    with ThreadPoolExecutor(max_workers=max_pool) as pool:
        future_map: dict[Future[dict[str, Any]], str] = {
            pool.submit(
                run_stock_deep_research,
                code=code,
                output_dir=output_dir,
                skill_root=skill_root,
                per_stock_timeout_sec=per_stock_timeout_sec,
                post_limit=post_limit,
                detail_limit=detail_limit,
                notice_days=notice_days,
                quotes_count=quotes_count,
                zh_page=zh_page,
                zh_count=zh_count,
            ): code
            for code in unique_codes
        }

        pending = set(future_map)
        while pending:
            wait_timeout = None
            if deadline is not None:
                remain = deadline - time.monotonic()
                if remain <= 0:
                    break
                wait_timeout = remain

            done, pending = wait(pending, timeout=wait_timeout, return_when=FIRST_COMPLETED)
            if not done:
                break
            for future in done:
                code = future_map[future]
                try:
                    rows.append(future.result())
                except Exception as exc:  # pragma: no cover - 防御性分支
                    rows.append(
                        {
                            "code": code,
                            "full_code": normalize_full_code(code),
                            "status": "error",
                            "error": f"unexpected_exception: {exc}",
                            "elapsed_sec": 0.0,
                            "steps": [],
                        }
                    )

        if pending:
            for future in pending:
                code = future_map[future]
                future.cancel()
                rows.append(
                    {
                        "code": code,
                        "full_code": normalize_full_code(code),
                        "status": "timeout",
                        "error": "batch_total_timeout",
                        "elapsed_sec": round(max(0.0, time.monotonic() - start), 3),
                        "steps": [],
                    }
                )

    order = {code: idx for idx, code in enumerate(unique_codes)}
    rows.sort(key=lambda row: order.get(str(row.get("code", "")), 10**6))
    return {"ok": True, "rows": rows, "elapsed_sec": round(time.monotonic() - start, 3)}


def _load_codes(args: argparse.Namespace) -> list[str]:
    if args.codes:
        return [item.strip() for item in args.codes.split(",") if item.strip()]
    if args.candidates_file:
        payload = json.loads(Path(args.candidates_file).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return []
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            return []
        out: list[str] = []
        for item in candidates:
            if isinstance(item, dict) and isinstance(item.get("code"), str):
                out.append(item["code"])
        return out
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="批量执行第3.5步个股深度分析")
    parser.add_argument("--codes", default="", help="股票代码列表，逗号分隔，如 002413,600519")
    parser.add_argument("--candidates-file", default="", help="candidates.json 路径（自动读取其中 code）")
    parser.add_argument("--output-dir", required=True, help="输出目录，如 /tmp/a-share-review/{DATE}")
    parser.add_argument("--skill-root", default=str(_SKILL_ROOT), help="Skill 根目录")
    parser.add_argument("--max-workers", type=int, default=4, help="并发数上限")
    parser.add_argument("--per-stock-timeout-sec", type=float, default=180, help="单票总超时秒数")
    parser.add_argument("--total-timeout-sec", type=float, default=900, help="批次总超时秒数")
    parser.add_argument("--post-limit", type=int, default=36, help="东方财富帖子抓取条数")
    parser.add_argument("--detail-limit", type=int, default=5, help="东方财富正文抓取条数")
    parser.add_argument("--notice-days", type=int, default=3, help="公告近N天")
    parser.add_argument("--quotes-count", type=int, default=8, help="淘股吧讨论条数")
    parser.add_argument("--zh-page", type=int, default=1, help="淘股吧综合推荐页码")
    parser.add_argument("--zh-count", type=int, default=20, help="淘股吧综合推荐条数")
    args = parser.parse_args()

    codes = _load_codes(args)
    if not codes:
        print(json.dumps({"ok": False, "error": "未提供可用股票代码"}, ensure_ascii=False))
        raise SystemExit(1)

    output_dir = Path(args.output_dir)
    result = run_batch_deep_research(
        codes=codes,
        output_dir=output_dir,
        skill_root=Path(args.skill_root),
        max_workers=args.max_workers,
        per_stock_timeout_sec=args.per_stock_timeout_sec,
        total_timeout_sec=args.total_timeout_sec,
        post_limit=args.post_limit,
        detail_limit=args.detail_limit,
        notice_days=args.notice_days,
        quotes_count=args.quotes_count,
        zh_page=args.zh_page,
        zh_count=args.zh_count,
    )
    if not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    report_path = write_timing_report(output_dir=output_dir, rows=result["rows"])
    summary = {
        "ok": True,
        "codes": len(codes),
        "elapsed_sec": result["elapsed_sec"],
        "timing_file": str(report_path),
        "status_count": {
            "ok": sum(1 for row in result["rows"] if row.get("status") == "ok"),
            "error": sum(1 for row in result["rows"] if row.get("status") == "error"),
            "timeout": sum(1 for row in result["rows"] if row.get("status") == "timeout"),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
