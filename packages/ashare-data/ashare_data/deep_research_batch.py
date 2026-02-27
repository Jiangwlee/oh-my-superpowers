"""批量执行个股深研预处理（采集 + LLM 生成 brief）。"""

from __future__ import annotations

import json
import subprocess
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


_STOCK_BRIEF_TEMPLATE = """你是一位 A 股个股研究分析师。请对 {CODE} {NAME} 做深度研究。\n\n股票背景：\n{CONTEXT}\n\n请读取附件中的个股数据文件并输出 Markdown 报告。\n\n输出必须严格按以下结构：\n\n# {CODE} {NAME} 深度研究报告\n\n## 信号汇总\n\n### 正面信号\n| 信号 | 来源级别 | 时效 | 来源摘要 |\n|------|---------|------|---------|\n| ... | ... | ... | ... |\n\n### 负面信号\n| 信号 | 来源级别 | 时效 | 来源摘要 |\n|------|---------|------|---------|\n| ... | ... | ... | ... |\n\n### 不确定信息\n- ...\n\n## 社区情绪\n- 热度\n- 多空比\n- 焦点话题\n\n## 仓位校准建议\n- 仓位乘数\n- 情绪标签\n- 调整依据\n- 入场时机建议\n\n## 关键风险提示\n1. ...\n2. ...\n\n请将完整 Markdown 直接输出到 stdout，并以一级标题 `#` 开头。\n"""


@dataclass
class CommandResult:
    """命令执行结果。"""

    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str], float], CommandResult]


@dataclass
class DeepResearchTarget:
    """深研目标。"""

    code: str
    name: str = ""
    context: str = ""


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


def _extract_markdown_from_stdout(stdout: str) -> str:
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[i:]).strip()
    return ""


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
    raw_output_dir: Path,
    code: str,
    full_code: str,
    post_limit: int,
    detail_limit: int,
    notice_days: int,
    quotes_count: int,
    zh_page: int,
    zh_count: int,
) -> list[tuple[str, list[str]]]:
    em_raw = raw_output_dir / f"dr_{code}_em.json"
    tgb_raw = raw_output_dir / f"dr_{code}_tgb.json"
    return [
        (
            "eastmoney",
            [
                "ashare-em-collect",
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
                "ashare-tgb-collect",
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
    ]


def _run_llm_brief(
    *,
    target: DeepResearchTarget,
    data_dir: Path,
    model: str,
    timeout_sec: float,
) -> tuple[str, str]:
    code = target.code
    name = target.name or code
    context = target.context or f"{code} 为预处理候选标的，请做简要深研。"

    em_raw = data_dir / "raw" / "deep_research" / f"dr_{code}_em.json"
    tgb_raw = data_dir / "raw" / "deep_research" / f"dr_{code}_tgb.json"
    brief_path = data_dir / "report" / f"dr_{code}_brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = (
        _STOCK_BRIEF_TEMPLATE.replace("{CODE}", code)
        .replace("{NAME}", name)
        .replace("{CONTEXT}", context)
    )

    cmd = [
        "opencode",
        "run",
        "--model",
        model,
        "--title",
        f"个股深研-{code}",
        "--file",
        str(em_raw),
        "--file",
        str(tgb_raw),
    ]

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=max(1.0, timeout_sec),
        check=False,
        cwd=str(Path.home()),
    )
    if result.returncode != 0:
        return "", (result.stderr or "opencode_return_nonzero")[:500]

    content = _extract_markdown_from_stdout(result.stdout or "")
    if not content:
        return "", "opencode_stdout_no_markdown"

    brief_path.write_text(content, encoding="utf-8")
    return str(brief_path), ""


def run_stock_deep_research(
    *,
    target: DeepResearchTarget,
    data_dir: Path,
    per_stock_timeout_sec: float,
    llm_model: str,
    command_runner: CommandRunner | None = None,
    post_limit: int = 36,
    detail_limit: int = 5,
    notice_days: int = 3,
    quotes_count: int = 8,
    zh_page: int = 1,
    zh_count: int = 20,
) -> dict[str, Any]:
    """执行单只股票深研：采集 + LLM brief。"""
    runner = command_runner or _default_command_runner
    stock_start = time.monotonic()
    code = target.code
    full_code = normalize_full_code(code)
    steps: list[dict[str, Any]] = []
    raw_output_dir = data_dir / "raw" / "deep_research"
    raw_output_dir.mkdir(parents=True, exist_ok=True)

    commands = _build_stock_commands(
        raw_output_dir=raw_output_dir,
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

    if status == "ok":
        llm_start = time.monotonic()
        elapsed_before = llm_start - stock_start
        remain = per_stock_timeout_sec - elapsed_before
        llm_step: dict[str, Any] = {
            "name": "brief_llm",
            "cmd": ["opencode", "run", "--model", llm_model],
            "status": "ok",
            "elapsed_sec": 0.0,
            "stderr": "",
            "output": "",
        }
        if remain <= 0:
            llm_step["status"] = "timeout"
            llm_step["stderr"] = "step_timeout"
            status = "timeout"
            error = "brief_llm_timeout"
            steps.append(llm_step)
        else:
            try:
                output_path, err = _run_llm_brief(
                    target=target,
                    data_dir=data_dir,
                    model=llm_model,
                    timeout_sec=remain,
                )
                llm_step["elapsed_sec"] = round(time.monotonic() - llm_start, 3)
                llm_step["output"] = output_path
                if err:
                    llm_step["status"] = "error"
                    llm_step["stderr"] = err
                    status = "error"
                    error = "brief_llm_failed"
            except subprocess.TimeoutExpired:
                llm_step["elapsed_sec"] = round(time.monotonic() - llm_start, 3)
                llm_step["status"] = "timeout"
                llm_step["stderr"] = "step_timeout"
                status = "timeout"
                error = "brief_llm_timeout"
            steps.append(llm_step)

    return {
        "code": code,
        "name": target.name,
        "full_code": full_code,
        "status": status,
        "error": error or None,
        "elapsed_sec": round(time.monotonic() - stock_start, 3),
        "steps": steps,
    }


def run_batch_deep_research(
    *,
    targets: list[DeepResearchTarget],
    data_dir: Path,
    llm_model: str,
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
    """并行执行多只股票深研。"""
    start = time.monotonic()

    unique_targets: list[DeepResearchTarget] = []
    seen: set[str] = set()
    for target in targets:
        normalized = "".join(ch for ch in target.code if ch.isdigit())
        if len(normalized) != 6 or normalized in seen:
            continue
        seen.add(normalized)
        unique_targets.append(
            DeepResearchTarget(
                code=normalized,
                name=target.name,
                context=target.context,
            )
        )

    if not unique_targets:
        return {"ok": False, "error": "no_valid_targets", "rows": []}

    rows: list[dict[str, Any]] = []
    max_pool = max(1, min(max_workers, len(unique_targets)))
    deadline = start + total_timeout_sec if total_timeout_sec > 0 else None

    with ThreadPoolExecutor(max_workers=max_pool) as pool:
        future_map: dict[Future[dict[str, Any]], str] = {
            pool.submit(
                run_stock_deep_research,
                target=target,
                data_dir=data_dir,
                llm_model=llm_model,
                per_stock_timeout_sec=per_stock_timeout_sec,
                post_limit=post_limit,
                detail_limit=detail_limit,
                notice_days=notice_days,
                quotes_count=quotes_count,
                zh_page=zh_page,
                zh_count=zh_count,
            ): target.code
            for target in unique_targets
        }

        pending = set(future_map)
        while pending:
            wait_timeout = None
            if deadline is not None:
                remain = deadline - time.monotonic()
                if remain <= 0:
                    break
                wait_timeout = remain

            done, pending = wait(
                pending, timeout=wait_timeout, return_when=FIRST_COMPLETED
            )
            if not done:
                break
            for future in done:
                code = future_map[future]
                try:
                    rows.append(future.result())
                except Exception as exc:  # pragma: no cover
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

    order = {target.code: idx for idx, target in enumerate(unique_targets)}
    rows.sort(key=lambda row: order.get(str(row.get("code", "")), 10**6))
    return {"ok": True, "rows": rows, "elapsed_sec": round(time.monotonic() - start, 3)}


def write_timing_report(*, data_dir: Path, rows: list[dict[str, Any]]) -> Path:
    """写入深研耗时报告。"""
    summary = {
        "total": len(rows),
        "ok": sum(1 for row in rows if row.get("status") == "ok"),
        "error": sum(1 for row in rows if row.get("status") == "error"),
        "timeout": sum(1 for row in rows if row.get("status") == "timeout"),
        "elapsed_sec_sum": round(
            sum(float(row.get("elapsed_sec", 0.0)) for row in rows), 3
        ),
    }
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "stocks": rows,
    }
    report_dir = data_dir / "analysis" / "deep_research"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "dr_timing.json"
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report_path
