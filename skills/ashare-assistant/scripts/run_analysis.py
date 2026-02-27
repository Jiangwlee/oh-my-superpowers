#!/usr/bin/env python3
"""运行子代理分析，将 filtered/ 中的大文件交给子代理生成 report/。

子代理使用 OpenCode CLI (`opencode run`) 实现，每个子代理独立运行一个会话。
支持完整流水线：

  第一轮（并行）: news + social → 情绪分析报告
  第二轮: review → 复盘报告 (market_review.md)
  第三轮: candidates → 候选股提取 (candidates.json)
  第四轮: 使用预处理深研报告 (report/dr_*_brief.md)
  第五轮: plan → 交易计划 (trading_plan.md)

用法:
    # 运行完整流水线（news → social → review → candidates → plan）
    python3 scripts/run_analysis.py \
        --data-dir ~/.ashare-assistant/data/2026-02-24 \
        --tasks all

    # 运行单个任务
    python3 scripts/run_analysis.py \
        --data-dir ~/.ashare-assistant/data/2026-02-24 \
        --tasks review
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time

logger = logging.getLogger(__name__)

# 脚本所在目录
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_SCRIPT_DIR, "prompts")
_SKILL_DIR = os.path.dirname(_SCRIPT_DIR)  # skills/ashare-assistant/

# ── 模型配置 ──────────────────────────────────────────

_DEFAULT_MODEL = "github-copilot/gpt-5-mini"

_MODEL_OVERRIDES: dict[str, str] = {
    "news": "deepseek/deepseek-reasoner",
    "social": "deepseek/deepseek-reasoner",
    "review": "deepseek/deepseek-reasoner",
    "candidates": "github-copilot/gpt-5-mini",
    "plan": "deepseek/deepseek-reasoner",
}

# ── 超时配置 ──────────────────────────────────────────

_TIMEOUT_OVERRIDES: dict[str, int] = {
    "review": 600,
    "candidates": 120,
    "plan": 600,
}

_DEFAULT_TIMEOUT = 300

# ── 子代理任务定义 ────────────────────────────────────

# 新闻情绪分析的输入文件
_NEWS_FILES = [
    "news_headline.md",
    "news_daily.md",
    "news_opportunity.md",
    "news_realtime.md",
    "news_flash.md",
]

# 社交情绪分析的输入文件
_SOCIAL_FILES = [
    "taoguba_hot.md",
    "taoguba_recommend.md",
    "taoguba_hot_discussion.md",
]

# 复盘报告需要的 filtered/ 直读文件（非 news/social 的小文件）
_REVIEW_DIRECT_FILES = [
    "us_market.md",
    "market_sectors.md",
    "funding.md",
    "ths_report.md",
    "trend_report.md",
    "run_id.md",
    "trade_date.md",
    "collection_summary.md",
]

# 复盘报告需要的 report/ 子代理分析报告
_REVIEW_REPORT_FILES = [
    "news_sentiment.md",
    "social_sentiment.md",
]

# 策略与演化文件（相对于 skill 目录）
_STRATEGY_FILES = [
    "strategy/active.yaml",
    "strategy/default.yaml",
]

_EVOLUTION_FILES = [
    "evolution/known_pitfalls.md",
    "evolution/selection_rules.md",
    "evolution/feedback.md",
]

# 脚本分析输出文件（相对于 data_dir）
_SCRIPT_OUTPUT_FILES = [
    "analysis/trade_review.json",
    "analysis/holding_insight.json",
]


def _analysis_dir(data_dir: str) -> str:
    return os.path.join(data_dir, "analysis")


def _candidates_output_path(data_dir: str) -> str:
    return os.path.join(_analysis_dir(data_dir), "candidates.json")


def _find_candidates_path(data_dir: str) -> str | None:
    path = _candidates_output_path(data_dir)
    if os.path.exists(path):
        return path
    return None


def _find_script_output_paths(data_dir: str) -> list[str]:
    """返回脚本分析 JSON 路径（仅新目录结构）。"""
    resolved: list[str] = []
    for name in ("trade_review.json", "holding_insight.json"):
        path = os.path.join(_analysis_dir(data_dir), name)
        if os.path.exists(path):
            resolved.append(path)
    return resolved


def _get_model(task: str, cli_model: str | None = None) -> str:
    """获取任务对应的模型。

    优先级: CLI --model > _MODEL_OVERRIDES > _DEFAULT_MODEL
    """
    if cli_model:
        return cli_model
    return _MODEL_OVERRIDES.get(task, _DEFAULT_MODEL)


def _get_timeout(task: str, cli_timeout: int | None = None) -> int:
    """获取任务对应的超时时间。

    优先级: CLI --timeout > _TIMEOUT_OVERRIDES > _DEFAULT_TIMEOUT
    """
    if cli_timeout is not None:
        return cli_timeout
    return _TIMEOUT_OVERRIDES.get(task, _DEFAULT_TIMEOUT)


def _load_prompt_template(template_name: str) -> str:
    """加载 prompt 模板文件。"""
    path = os.path.join(_PROMPTS_DIR, f"{template_name}.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt 模板不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_files_section(base_dir: str, filenames: list[str]) -> str:
    """构建文件列表部分，包含绝对路径。

    只列出实际存在的文件。返回 Markdown 格式的文件列表。

    Args:
        base_dir: 基础目录。
        filenames: 相对于 base_dir 的文件名列表。
    """
    lines = []
    for fname in filenames:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            lines.append(f"- `{fpath}` ({size_kb:.1f} KB)")
        else:
            logger.warning("文件不存在，跳过: %s", fpath)
    if not lines:
        return "（无可用文件）"
    return "\n".join(lines)


def _collect_existing_files(base_dir: str, filenames: list[str]) -> list[str]:
    """收集存在的文件绝对路径列表。"""
    result = []
    for fname in filenames:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            result.append(fpath)
    return result


def _extract_date_from_data_dir(data_dir: str) -> str:
    """从 data_dir 路径中提取日期（最后一级目录名）。"""
    return os.path.basename(data_dir.rstrip("/"))


def _run_opencode(
    prompt: str,
    output_path: str,
    title: str,
    attached_files: list[str] | None = None,
    model: str | None = None,
    timeout: int = 300,
    overwrite: bool = False,
    output_format: str = "markdown",
) -> bool:
    """调用 opencode run 执行子代理任务。

    Args:
        prompt: 完整的 prompt 文本。
        output_path: 子代理输出应写入的文件路径。
        title: 会话标题。
        attached_files: 附加文件列表（使用 --file 参数）。
        model: 模型名称（如 "anthropic/claude-sonnet-4-20250514"）。
        timeout: 超时时间（秒）。
        overwrite: 强制覆盖已存在的输出文件。
        output_format: 输出格式，"markdown" 或 "json"。

    Returns:
        True 如果成功，False 如果失败。
    """
    # 幂等跳过：输出文件已存在且非空时直接复用
    if (
        not overwrite
        and os.path.exists(output_path)
        and os.path.getsize(output_path) > 0
    ):
        size_kb = os.path.getsize(output_path) / 1024
        logger.info("跳过（已存在）: %s (%.1f KB)", title, size_kb)
        return True

    # 在 prompt 末尾追加输出指令（按格式区分）
    if output_format == "json":
        output_instruction = (
            "请将完整的 JSON 结果直接输出到终端（stdout）。\n"
            "输出必须以 `{` 开头，以 `}` 结尾，中间是合法的 JSON。\n"
            "不要输出任何 Markdown、注释或解释文字。"
        )
    else:
        output_instruction = (
            "请将完整的 Markdown 分析结果直接输出到终端（stdout）。\n"
            "输出必须以 `#` 开头的一级标题开始，之后是完整的分析内容。"
        )
    full_prompt = f"{prompt}\n\n---\n\n{output_instruction}"

    cmd = ["opencode", "run"]

    if model:
        cmd.extend(["--model", model])

    cmd.extend(["--title", title])

    # 附加文件
    if attached_files:
        for fpath in attached_files:
            if os.path.exists(fpath):
                cmd.extend(["--file", fpath])

    # prompt 通过 stdin 传入（避免 shell 转义和长参数问题）
    logger.info("启动子代理: %s", title)
    logger.debug("命令: %s", " ".join(cmd[:6]) + " ...")

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser("~"),
        )
        elapsed = time.time() - start_time

        if result.returncode != 0:
            logger.error(
                "子代理失败 (%s): returncode=%d, stderr=%s",
                title,
                result.returncode,
                result.stderr[:500] if result.stderr else "(empty)",
            )
            return False

        # 从 stdout 提取内容并写入输出文件
        stdout = result.stdout or ""
        if not stdout.strip():
            logger.error("子代理完成但 stdout 为空: %s (%.1f秒)", title, elapsed)
            return False

        if output_format == "json":
            content = _extract_json_from_stdout(stdout)
            if not content:
                logger.error(
                    "子代理 stdout 无合法 JSON 内容: %s (%.1f秒)",
                    title,
                    elapsed,
                )
                logger.debug("stdout 前500字符: %s", stdout[:500])
                return False
        else:
            content = _extract_markdown_from_stdout(stdout)
            if not content:
                logger.error(
                    "子代理 stdout 无 Markdown 内容（未找到 # 标题）: %s (%.1f秒)",
                    title,
                    elapsed,
                )
                logger.debug("stdout 前500字符: %s", stdout[:500])
                return False

        if parent := os.path.dirname(output_path):
            os.makedirs(parent, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        size_kb = len(content) / 1024
        logger.info("子代理完成: %s (%.1f秒, 输出 %.1f KB)", title, elapsed, size_kb)
        return True

    except subprocess.TimeoutExpired:
        logger.error("子代理超时 (%s): %d 秒", title, timeout)
        return False
    except FileNotFoundError:
        logger.error("opencode 命令未找到，请确认已安装 OpenCode CLI")
        return False
    except Exception as e:
        logger.exception("子代理异常 (%s): %s", title, e)
        return False


def _extract_markdown_from_stdout(stdout: str) -> str:
    """从 stdout 提取 Markdown 内容（从第一个 # 标题开始）。

    Returns:
        提取的 Markdown 文本，未找到时返回空字符串。
    """
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[i:])
    return ""


def _extract_json_from_stdout(stdout: str) -> str:
    """从 stdout 提取 JSON 内容（第一个 { 到最后一个 } 之间的内容）。

    子代理可能在 JSON 前后输出解释性文字，此函数只提取 JSON 部分。

    Returns:
        提取的 JSON 文本，未找到或解析失败时返回空字符串。
    """
    first_brace = stdout.find("{")
    last_brace = stdout.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        return ""
    candidate = stdout[first_brace : last_brace + 1]
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        return ""


# ── 任务实现 ──────────────────────────────────────────


def run_news_sentiment(
    data_dir: str, model: str | None = None, timeout: int = 300, overwrite: bool = False
) -> bool:
    """运行新闻情绪分析子代理。"""
    filtered_dir = os.path.join(data_dir, "filtered")
    report_dir = os.path.join(data_dir, "report")
    os.makedirs(report_dir, exist_ok=True)

    # 加载模板并替换占位符
    template = _load_prompt_template("news_sentiment")
    files_section = _build_files_section(filtered_dir, _NEWS_FILES)
    prompt = template.replace("{FILES_SECTION}", files_section)

    # 输出路径
    output_path = os.path.join(report_dir, "news_sentiment.md")

    # 附加文件列表（存在的文件）
    attached_files = [
        os.path.join(filtered_dir, f)
        for f in _NEWS_FILES
        if os.path.exists(os.path.join(filtered_dir, f))
    ]

    return _run_opencode(
        prompt=prompt,
        output_path=output_path,
        title="新闻情绪分析",
        attached_files=attached_files,
        model=model,
        timeout=timeout,
        overwrite=overwrite,
    )


def run_social_sentiment(
    data_dir: str, model: str | None = None, timeout: int = 300, overwrite: bool = False
) -> bool:
    """运行社交情绪分析子代理。"""
    filtered_dir = os.path.join(data_dir, "filtered")
    report_dir = os.path.join(data_dir, "report")
    os.makedirs(report_dir, exist_ok=True)

    template = _load_prompt_template("social_sentiment")
    files_section = _build_files_section(filtered_dir, _SOCIAL_FILES)
    prompt = template.replace("{FILES_SECTION}", files_section)

    output_path = os.path.join(report_dir, "social_sentiment.md")

    attached_files = [
        os.path.join(filtered_dir, f)
        for f in _SOCIAL_FILES
        if os.path.exists(os.path.join(filtered_dir, f))
    ]

    return _run_opencode(
        prompt=prompt,
        output_path=output_path,
        title="社交情绪分析",
        attached_files=attached_files,
        model=model,
        timeout=timeout,
        overwrite=overwrite,
    )


def run_market_review(
    data_dir: str, model: str | None = None, timeout: int = 300, overwrite: bool = False
) -> bool:
    """运行复盘报告生成子代理。

    输入: report/news_sentiment.md, report/social_sentiment.md,
          filtered/ 直读文件, strategy/, evolution/ 文件
    输出: {data_dir}/market_review.md
    """
    filtered_dir = os.path.join(data_dir, "filtered")
    report_dir = os.path.join(data_dir, "report")

    # 检查前置依赖
    for dep_file in _REVIEW_REPORT_FILES:
        dep_path = os.path.join(report_dir, dep_file)
        if not os.path.exists(dep_path):
            logger.warning("前置报告不存在: %s（review 质量可能受影响）", dep_path)

    # 加载模板并替换占位符
    template = _load_prompt_template("market_review")
    date_str = _extract_date_from_data_dir(data_dir)

    # 构建各部分文件列表
    report_files_section = _build_files_section(report_dir, _REVIEW_REPORT_FILES)
    direct_files_section = _build_files_section(filtered_dir, _REVIEW_DIRECT_FILES)

    # 策略与演化文件（合并为一个 section）
    extra_files = []
    extra_files.extend(_collect_existing_files(_SKILL_DIR, _STRATEGY_FILES))
    extra_files.extend(_collect_existing_files(_SKILL_DIR, _EVOLUTION_FILES))
    if extra_files:
        extra_section_lines = []
        for fpath in extra_files:
            size_kb = os.path.getsize(fpath) / 1024
            extra_section_lines.append(f"- `{fpath}` ({size_kb:.1f} KB)")
        extra_files_section = "\n".join(extra_section_lines)
    else:
        extra_files_section = "（无可用文件）"

    prompt = (
        template.replace("{DATE}", date_str)
        .replace("{REPORT_FILES_SECTION}", report_files_section)
        .replace("{DIRECT_FILES_SECTION}", direct_files_section)
        .replace("{EXTRA_FILES_SECTION}", extra_files_section)
    )

    # 输出路径
    output_path = os.path.join(data_dir, "market_review.md")

    # 附加文件：report 报告 + filtered 直读 + 策略/演化
    attached_files = []
    attached_files.extend(_collect_existing_files(report_dir, _REVIEW_REPORT_FILES))
    attached_files.extend(_collect_existing_files(filtered_dir, _REVIEW_DIRECT_FILES))
    attached_files.extend(extra_files)

    return _run_opencode(
        prompt=prompt,
        output_path=output_path,
        title="复盘报告生成",
        attached_files=attached_files,
        model=model,
        timeout=timeout,
        overwrite=overwrite,
    )


def run_candidates(
    data_dir: str, model: str | None = None, timeout: int = 300, overwrite: bool = False
) -> bool:
    """运行候选股提取子代理。

    从 market_review.md 中提取候选股列表，生成 candidates.json。
    这是一个轻量级 LLM 调用，输入仅为复盘报告，输出为结构化 JSON。

    输入: market_review.md, strategy/
    输出: {data_dir}/analysis/candidates.json
    """
    # 检查前置依赖
    review_path = os.path.join(data_dir, "market_review.md")
    if not os.path.exists(review_path):
        logger.error("market_review.md 不存在: %s\n请先运行 review 任务", review_path)
        return False

    # 加载模板并替换占位符
    template = _load_prompt_template("candidates")
    date_str = _extract_date_from_data_dir(data_dir)

    # 策略文件
    strategy_files = _collect_existing_files(_SKILL_DIR, _STRATEGY_FILES)
    if strategy_files:
        strategy_section_lines = []
        for fpath in strategy_files:
            size_kb = os.path.getsize(fpath) / 1024
            strategy_section_lines.append(f"- `{fpath}` ({size_kb:.1f} KB)")
        strategy_files_section = "\n".join(strategy_section_lines)
    else:
        strategy_files_section = "（无可用文件）"

    prompt = (
        template.replace("{DATE}", date_str)
        .replace("{REVIEW_FILE}", review_path)
        .replace("{STRATEGY_FILES_SECTION}", strategy_files_section)
    )

    # 输出路径
    candidates_output = _candidates_output_path(data_dir)
    os.makedirs(os.path.dirname(candidates_output), exist_ok=True)

    # 附加文件
    attached_files = [review_path]
    attached_files.extend(strategy_files)
    # run_id.md 用于提取 run_id 字段
    run_id_path = os.path.join(data_dir, "filtered", "run_id.md")
    if os.path.exists(run_id_path):
        attached_files.append(run_id_path)

    return _run_opencode(
        prompt=prompt,
        output_path=candidates_output,
        title="候选股提取",
        attached_files=attached_files,
        model=model,
        timeout=timeout,
        overwrite=overwrite,
        output_format="json",
    )


def run_trading_plan(
    data_dir: str, model: str | None = None, timeout: int = 300, overwrite: bool = False
) -> bool:
    """运行交易计划生成子代理。

    输入: market_review.md, report/dr_*_brief.md,
          trade_review.json, holding_insight.json, strategy/, evolution/
    输出: {data_dir}/trading_plan.md
    """
    report_dir = os.path.join(data_dir, "report")

    # 检查前置依赖（复盘报告）
    review_path = os.path.join(data_dir, "market_review.md")
    if not os.path.exists(review_path):
        logger.error("market_review.md 不存在: %s\n请先运行 review 任务", review_path)
        return False

    # 加载模板并替换占位符
    template = _load_prompt_template("trading_plan")
    date_str = _extract_date_from_data_dir(data_dir)

    # 收集个股深研报告
    dr_files: list[str] = []
    if os.path.exists(report_dir):
        for fname in sorted(os.listdir(report_dir)):
            if fname.startswith("dr_") and fname.endswith("_brief.md"):
                dr_files.append(os.path.join(report_dir, fname))

    if dr_files:
        dr_section_lines = []
        for fpath in dr_files:
            size_kb = os.path.getsize(fpath) / 1024
            dr_section_lines.append(f"- `{fpath}` ({size_kb:.1f} KB)")
        dr_files_section = "\n".join(dr_section_lines)
    else:
        dr_files_section = "（无个股深研报告，仓位乘数默认 ×1.0）"

    # 脚本分析输出文件（仅新目录结构）
    script_output_paths = _find_script_output_paths(data_dir)
    if script_output_paths:
        script_section_lines = []
        for fpath in script_output_paths:
            size_kb = os.path.getsize(fpath) / 1024
            script_section_lines.append(f"- `{fpath}` ({size_kb:.1f} KB)")
        script_files_section = "\n".join(script_section_lines)
    else:
        script_files_section = "（无可用文件）"

    # 策略与演化文件
    strategy_files = []
    strategy_files.extend(_collect_existing_files(_SKILL_DIR, _STRATEGY_FILES))
    strategy_files.extend(_collect_existing_files(_SKILL_DIR, _EVOLUTION_FILES))
    if strategy_files:
        strategy_section_lines = []
        for fpath in strategy_files:
            size_kb = os.path.getsize(fpath) / 1024
            strategy_section_lines.append(f"- `{fpath}` ({size_kb:.1f} KB)")
        strategy_files_section = "\n".join(strategy_section_lines)
    else:
        strategy_files_section = "（无可用文件）"

    # 输出路径
    trading_plan_output = os.path.join(data_dir, "trading_plan.md")

    prompt = (
        template.replace("{DATE}", date_str)
        .replace("{REVIEW_FILE}", review_path)
        .replace("{DR_FILES_SECTION}", dr_files_section)
        .replace("{SCRIPT_FILES_SECTION}", script_files_section)
        .replace("{STRATEGY_FILES_SECTION}", strategy_files_section)
        .replace("{TRADING_PLAN_OUTPUT}", trading_plan_output)
    )

    # 附加文件
    attached_files = [review_path]
    attached_files.extend(dr_files)
    attached_files.extend(script_output_paths)
    attached_files.extend(strategy_files)

    return _run_opencode(
        prompt=prompt,
        output_path=trading_plan_output,
        title="交易计划生成",
        attached_files=attached_files,
        model=model,
        timeout=timeout,
        overwrite=overwrite,
    )


# ── 索引生成 ──────────────────────────────────────────


def generate_report_index(data_dir: str) -> None:
    """生成 report/index.md 索引文件。"""
    report_dir = os.path.join(data_dir, "report")
    if not os.path.exists(report_dir):
        logger.warning("report/ 目录不存在: %s", report_dir)
        return

    as_of_date = os.path.basename(data_dir.rstrip("/"))

    lines = [f"# 分析报告索引 {as_of_date}", ""]
    lines.append("本目录包含子代理生成的中间分析报告，供主 agent 做最终复盘时读取。")
    lines.append("")

    total_size = 0.0
    file_count = 0

    lines.append("| 文件 | 大小(KB) | 说明 |")
    lines.append("|------|---------|------|")

    _REPORT_DESCRIPTIONS = {
        "news_sentiment.md": "新闻情绪分析",
        "social_sentiment.md": "社交情绪分析",
    }

    for fname in sorted(os.listdir(report_dir)):
        if fname == "index.md":
            continue
        fpath = os.path.join(report_dir, fname)
        if not os.path.isfile(fpath):
            continue
        size_kb = os.path.getsize(fpath) / 1024
        desc = _REPORT_DESCRIPTIONS.get(fname, "")
        if fname.startswith("dr_") and fname.endswith("_brief.md"):
            code = fname.replace("dr_", "").replace("_brief.md", "")
            desc = f"个股深研 {code}"
        lines.append(f"| {fname} | {size_kb:.1f} | {desc} |")
        total_size += size_kb
        file_count += 1

    lines.append("")
    lines.append(f"**总计**: {file_count} 个文件, {total_size:.1f} KB")
    lines.append("")

    index_path = os.path.join(report_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(
        "生成报告索引: %s (%d 文件, %.1f KB)", index_path, file_count, total_size
    )


# ── all 流水线辅助 ────────────────────────────────────


def _collect_deep_research_targets(data_dir: str) -> list[dict]:
    """从 candidates.json 读取 buy/watch 候选股。

    Returns:
        候选股列表，每项含 code/name/thesis_short，空列表表示无候选或读取失败。
    """
    candidates_path = _find_candidates_path(data_dir)
    if not candidates_path or not os.path.exists(candidates_path):
        return []
    try:
        with open(candidates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            c for c in data.get("candidates", []) if c.get("action") in ("buy", "watch")
        ]
    except Exception as e:
        logger.warning("读取 candidates.json 失败: %s", e)
        return []


def _run_all_pipeline(args: argparse.Namespace, data_dir: str) -> dict[str, bool]:
    """执行完整的 all 流水线。

    流程:
      1. news + social（情绪分析）
      2. review（复盘报告 → market_review.md）
      3. candidates（从复盘报告提取候选股 → candidates.json）
      4. 使用 ashare-data 预处理好的个股深研报告（dr_*_brief.md）
      4.5 执行前置脚本 trade_review.py 和 holding_insight.py
      5. plan（交易计划 → trading_plan.md，一次到位）
      6. 执行风控检查 risk_check.py 与决策日志 decision_logger.py

    Returns:
        各任务的成功状态字典。
    """
    results: dict[str, bool] = {}

    # ── 阶段 1: 情绪分析 ──────────────────────────────
    for task in ["news", "social"]:
        m = _get_model(task, args.model)
        t = _get_timeout(task, args.timeout)
        logger.info("任务 [%s] 使用模型: %s, 超时: %ds", task, m, t)
        if task == "news":
            results["news"] = run_news_sentiment(
                data_dir, model=m, timeout=t, overwrite=args.overwrite
            )
        else:
            results["social"] = run_social_sentiment(
                data_dir, model=m, timeout=t, overwrite=args.overwrite
            )

    # ── 阶段 2: 复盘报告 ──────────────────────────────
    m = _get_model("review", args.model)
    t = _get_timeout("review", args.timeout)
    logger.info("任务 [review] 使用模型: %s, 超时: %ds", m, t)
    results["review"] = run_market_review(
        data_dir, model=m, timeout=t, overwrite=args.overwrite
    )
    if not results["review"]:
        logger.error("review 失败，中止流水线")
        results["candidates"] = False
        results["plan"] = False
        return results

    # ── 阶段 3: 候选股提取 ────────────────────────────
    candidates_model = _get_model("candidates", args.model)
    candidates_timeout = _get_timeout("candidates", args.timeout)
    logger.info(
        "任务 [candidates] 使用模型: %s, 超时: %ds",
        candidates_model,
        candidates_timeout,
    )
    results["candidates"] = run_candidates(
        data_dir,
        model=candidates_model,
        timeout=candidates_timeout,
        overwrite=args.overwrite,
    )
    if not results["candidates"]:
        logger.error("candidates 提取失败，中止流水线")
        results["plan"] = False
        return results

    # ── 阶段 4: 读取预处理个股深研报告 ─────────────────────
    targets = _collect_deep_research_targets(data_dir)
    if targets:
        missing_codes: list[str] = []
        for c in targets:
            code = c["code"]
            brief_path = os.path.join(data_dir, "report", f"dr_{code}_brief.md")
            if not os.path.exists(brief_path):
                missing_codes.append(code)
        if missing_codes:
            logger.warning(
                "以下候选股缺少预处理深研报告（继续执行 plan）：%s",
                missing_codes,
            )
        else:
            logger.info(
                "候选股深研报告已就绪: %d 只",
                len(targets),
            )
    else:
        logger.info("无 buy/watch 候选股，跳过深研报告检查")

    # ── 阶段 4.5: 账户与持仓分析 (plan 的增强输入) ───────────
    trade_review_output = os.path.join(_analysis_dir(data_dir), "trade_review.json")
    holding_insight_output = os.path.join(_analysis_dir(data_dir), "holding_insight.json")
    strategy_path = os.path.join(_SKILL_DIR, "strategy", "active.yaml")

    logger.info("执行前置脚本: trade_review.py 和 holding_insight.py")
    try:
        trade_proc = subprocess.run(
            [
                sys.executable,
                os.path.join(_SCRIPT_DIR, "trade_review.py"),
                "--output",
                trade_review_output,
                "--strategy",
                strategy_path,
            ],
            cwd=_SKILL_DIR,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if trade_proc.returncode != 0:
            logger.warning(
                "trade_review.py 失败 (exit=%s): %s",
                trade_proc.returncode,
                (trade_proc.stderr or trade_proc.stdout or "").strip()[:300],
            )
            results["trade_review"] = False
        else:
            results["trade_review"] = True

        hold_proc = subprocess.run(
            [
                sys.executable,
                os.path.join(_SCRIPT_DIR, "holding_insight.py"),
                "--output",
                holding_insight_output,
                "--strategy",
                strategy_path,
            ],
            cwd=_SKILL_DIR,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if hold_proc.returncode != 0:
            logger.warning(
                "holding_insight.py 失败 (exit=%s): %s",
                hold_proc.returncode,
                (hold_proc.stderr or hold_proc.stdout or "").strip()[:300],
            )
            results["holding_insight"] = False
        else:
            results["holding_insight"] = True
    except subprocess.TimeoutExpired as e:
        logger.warning("执行 trade_review/holding_insight 超时: %s", e)
        results["trade_review"] = False
        results["holding_insight"] = False
    except Exception as e:
        logger.warning("执行 trade_review/holding_insight 异常: %s", e)
        results["trade_review"] = False
        results["holding_insight"] = False

    if not results.get("trade_review") or not results.get("holding_insight"):
        logger.error("trade_review 或 holding_insight 失败，中止流水线")
        results["plan"] = False
        return results

    # ── 阶段 5: 交易计划 ──────────────────────────────
    plan_model = _get_model("plan", args.model)
    plan_timeout = _get_timeout("plan", args.timeout)
    logger.info("任务 [plan] 使用模型: %s, 超时: %ds", plan_model, plan_timeout)
    results["plan"] = run_trading_plan(
        data_dir, model=plan_model, timeout=plan_timeout, overwrite=args.overwrite
    )
    if not results["plan"]:
        logger.error("plan 失败，中止流水线")
        return results

    # ── 阶段 6: 风控检查与决策日志记录（仅在 plan 成功后执行） ──
    candidates_file = _find_candidates_path(data_dir)
    if results.get("plan") and candidates_file and os.path.exists(candidates_file):
        logger.info("执行校验脚本: risk_check.py 和 decision_logger.py")
        try:
            risk_proc = subprocess.run(
                [
                    sys.executable,
                    os.path.join(_SCRIPT_DIR, "risk_check.py"),
                    "--input",
                    candidates_file,
                ],
                cwd=_SKILL_DIR,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if risk_proc.returncode != 0:
                logger.warning(
                    "risk_check.py 失败 (exit=%s): %s",
                    risk_proc.returncode,
                    (risk_proc.stderr or risk_proc.stdout or "").strip()[:300],
                )
                results["risk_check"] = False
                logger.info("risk_check 未通过，跳过 decision_logger.py")
                results["decision_logger"] = False
                return results
            else:
                results["risk_check"] = True

            decision_proc = subprocess.run(
                [
                    sys.executable,
                    os.path.join(_SCRIPT_DIR, "decision_logger.py"),
                    "--input",
                    candidates_file,
                ],
                cwd=_SKILL_DIR,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if decision_proc.returncode != 0:
                logger.warning(
                    "decision_logger.py 失败 (exit=%s): %s",
                    decision_proc.returncode,
                    (decision_proc.stderr or decision_proc.stdout or "").strip()[:300],
                )
                results["decision_logger"] = False
            else:
                results["decision_logger"] = True
        except subprocess.TimeoutExpired as e:
            logger.warning("执行 risk_check/decision_logger 超时: %s", e)
            results["risk_check"] = False
            results["decision_logger"] = False
        except Exception as e:
            logger.warning("执行 risk_check/decision_logger 异常: %s", e)
            results["risk_check"] = False
            results["decision_logger"] = False
    elif not results.get("plan"):
        logger.info("plan 未成功，跳过 risk_check/decision_logger")
    else:
        logger.info("analysis/candidates.json 不存在，跳过 risk_check/decision_logger")

    return results


# ── 主逻辑 ────────────────────────────────────────────


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="运行子代理分析（新闻情绪、社交情绪、复盘报告、交易计划）"
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help=(
            "数据根目录（如 ~/.ashare-assistant/data/2026-02-24）。"
            "不指定则自动使用 ~/.ashare-assistant/data/今日日期。"
        ),
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        choices=["news", "social", "review", "candidates", "plan", "all"],
        default=["all"],
        help="要运行的任务（默认 all = 情绪→复盘→候选股→交易计划）",
    )
    parser.add_argument(
        "--model",
        help="覆盖所有任务的模型（不指定则使用内置 per-task 映射）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="覆盖所有任务的超时时间（秒）",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="强制重新运行，忽略已存在的输出文件（覆盖幂等跳过）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[analysis] %(message)s",
    )

    if args.data_dir:
        data_dir = os.path.expanduser(args.data_dir)
    else:
        from ashare_data.core.config import data_dir_for_date

        data_dir = str(data_dir_for_date())
        logger.info("--data-dir 未指定，使用今日目录: %s", data_dir)

    # 检查 filtered/ 目录
    filtered_dir = os.path.join(data_dir, "filtered")
    if not os.path.exists(filtered_dir):
        logger.error(
            "filtered/ 目录不存在: %s\n请先运行 filter_to_markdown.py", filtered_dir
        )
        sys.exit(1)

    tasks = args.tasks
    start_time = time.time()

    # all 模式：走完整流水线（情绪→复盘→候选股→交易计划）
    if "all" in tasks:
        results = _run_all_pipeline(args, data_dir)
        generate_report_index(data_dir)
        elapsed = time.time() - start_time
        success = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)
        print(
            f"[analysis] 完成: {success} 成功, {failed} 失败 ({elapsed:.1f}秒)",
            file=sys.stderr,
        )
        for task_name, ok in results.items():
            print(
                f"[analysis]   {task_name}: {'OK' if ok else 'FAILED'}", file=sys.stderr
            )
        if failed > 0:
            sys.exit(1)
        return

    results: dict[str, bool] = {}

    for task in tasks:
        task_model = _get_model(task, args.model)
        task_timeout = _get_timeout(task, args.timeout)

        logger.info("任务 [%s] 使用模型: %s, 超时: %ds", task, task_model, task_timeout)

        if task == "news":
            results["news"] = run_news_sentiment(
                data_dir,
                model=task_model,
                timeout=task_timeout,
                overwrite=args.overwrite,
            )
        elif task == "social":
            results["social"] = run_social_sentiment(
                data_dir,
                model=task_model,
                timeout=task_timeout,
                overwrite=args.overwrite,
            )
        elif task == "review":
            results["review"] = run_market_review(
                data_dir,
                model=task_model,
                timeout=task_timeout,
                overwrite=args.overwrite,
            )
        elif task == "candidates":
            # candidates 依赖 review 成功
            if results.get("review") is False:
                logger.error("review 任务失败，跳过 candidates 任务（依赖流水线阻断）")
                results["candidates"] = False
            else:
                results["candidates"] = run_candidates(
                    data_dir,
                    model=task_model,
                    timeout=task_timeout,
                    overwrite=args.overwrite,
                )
        elif task == "plan":
            # plan 依赖 review 成功，如果 review 在本次运行中失败则阻断
            if results.get("review") is False:
                logger.error("review 任务失败，跳过 plan 任务（依赖流水线阻断）")
                results["plan"] = False
            else:
                results["plan"] = run_trading_plan(
                    data_dir,
                    model=task_model,
                    timeout=task_timeout,
                    overwrite=args.overwrite,
                )
    # 生成报告索引
    generate_report_index(data_dir)

    elapsed = time.time() - start_time

    # 输出摘要
    success = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(
        f"[analysis] 完成: {success} 成功, {failed} 失败 ({elapsed:.1f}秒)",
        file=sys.stderr,
    )
    for task_name, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"[analysis]   {task_name}: {status}", file=sys.stderr)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
