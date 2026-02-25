#!/usr/bin/env python3
"""运行子代理分析，将 filtered/ 中的大文件交给子代理生成 report/。

子代理使用 OpenCode CLI (`opencode run`) 实现，每个子代理独立运行一个会话。
支持完整的 4+N 轮子代理流水线：

  第一轮（并行）: news + social → 情绪分析报告
  第二轮: review → 复盘报告 (market_review.md)
  第三轮（并行）: stock ×N → 个股深研
  第四轮: plan → 交易计划 (trading_plan.md + candidates.json)

用法:
    # 运行完整流水线（news → social → review → plan）
    python3 scripts/run_analysis.py \
        --data-dir ~/.ashare-assistant/data/2026-02-24 \
        --tasks all

    # 运行单个任务
    python3 scripts/run_analysis.py \
        --data-dir ~/.ashare-assistant/data/2026-02-24 \
        --tasks review

    # 运行个股深研（需指定股票代码和名称）
    python3 scripts/run_analysis.py \
        --data-dir ~/.ashare-assistant/data/2026-02-24 \
        --tasks stock \
        --stock-code 002050 --stock-name 三花智控
"""

import argparse
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
    "plan": "deepseek/deepseek-reasoner",
    "stock": "github-copilot/gpt-5-mini",
}

# ── 超时配置 ──────────────────────────────────────────

_TIMEOUT_OVERRIDES: dict[str, int] = {
    "review": 600,
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
    "trade_review.json",
    "holding_insight.json",
]


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
) -> bool:
    """调用 opencode run 执行子代理任务。

    Args:
        prompt: 完整的 prompt 文本。
        output_path: 子代理输出应写入的文件路径。
        title: 会话标题。
        attached_files: 附加文件列表（使用 --file 参数）。
        model: 模型名称（如 "anthropic/claude-sonnet-4-20250514"）。
        timeout: 超时时间（秒）。

    Returns:
        True 如果成功，False 如果失败。
    """
    # 幂等跳过：输出文件已存在且非空时直接复用
    if not overwrite and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        size_kb = os.path.getsize(output_path) / 1024
        logger.info("跳过（已存在）: %s (%.1f KB)", title, size_kb)
        return True

    # 在 prompt 末尾追加输出指令
    full_prompt = (
        f"{prompt}\n\n"
        f"---\n\n"
        f"请将完整的 Markdown 分析结果直接输出到终端（stdout）。\n"
        f"不要使用 Write 工具写文件，直接输出文本即可。\n"
        f"输出必须以 `#` 开头的一级标题开始，之后是完整的分析内容。"
    )

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

        # 从 stdout 提取 Markdown 并写入输出文件
        stdout = result.stdout or ""
        if not stdout.strip():
            logger.error("子代理完成但 stdout 为空: %s (%.1f秒)", title, elapsed)
            return False

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


# ── 任务实现 ──────────────────────────────────────────


def run_news_sentiment(
    data_dir: str, model: str | None = None, timeout: int = 300
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
    )


def run_social_sentiment(
    data_dir: str, model: str | None = None, timeout: int = 300
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
    )


def run_stock_deep_research(
    data_dir: str,
    stock_code: str,
    stock_name: str,
    context: str = "",
    model: str | None = None,
    timeout: int = 300,
) -> bool:
    """运行个股深度研究子代理。

    Args:
        data_dir: 数据根目录。
        stock_code: 6位股票代码。
        stock_name: 股票名称。
        context: 选股上下文（为什么选这只股，来自第三步的信息）。
        model: 模型名称。
        timeout: 超时时间。
    """
    report_dir = os.path.join(data_dir, "report")
    os.makedirs(report_dir, exist_ok=True)

    template = _load_prompt_template("stock_deep_research")

    # 查找个股数据文件
    stock_files = []
    for pattern in [f"dr_{stock_code}_em.json", f"dr_{stock_code}_tgb.json"]:
        fpath = os.path.join(data_dir, pattern)
        if os.path.exists(fpath):
            stock_files.append(fpath)
        # 也检查 raw/ 子目录
        fpath_raw = os.path.join(data_dir, "raw", pattern)
        if os.path.exists(fpath_raw):
            stock_files.append(fpath_raw)

    if not stock_files:
        logger.error(
            "未找到 %s (%s) 的数据文件，请先运行采集脚本", stock_code, stock_name
        )
        return False

    files_section = "\n".join(f"- `{f}`" for f in stock_files)
    context_section = (
        context or f"该股票（{stock_code} {stock_name}）是第三步筛选出的候选股。"
    )

    prompt = (
        template.replace("{CODE}", stock_code)
        .replace("{NAME}", stock_name)
        .replace("{FILES_SECTION}", files_section)
        .replace("{CONTEXT_SECTION}", context_section)
    )

    output_path = os.path.join(report_dir, f"dr_{stock_code}_brief.md")

    return _run_opencode(
        prompt=prompt,
        output_path=output_path,
        title=f"个股深研-{stock_code}",
        attached_files=stock_files,
        model=model,
        timeout=timeout,
    )


def run_market_review(
    data_dir: str, model: str | None = None, timeout: int = 300
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
    )


def run_trading_plan(
    data_dir: str, model: str | None = None, timeout: int = 300
) -> bool:
    """运行交易计划生成子代理。

    输入: market_review.md, report/dr_*_brief.md,
          trade_review.json, holding_insight.json, strategy/, evolution/
    输出: {data_dir}/trading_plan.md + {data_dir}/candidates.json
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

    # 脚本分析输出文件
    script_files_section = _build_files_section(data_dir, _SCRIPT_OUTPUT_FILES)

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
    candidates_output = os.path.join(data_dir, "candidates.json")

    prompt = (
        template.replace("{DATE}", date_str)
        .replace("{REVIEW_FILE}", review_path)
        .replace("{DR_FILES_SECTION}", dr_files_section)
        .replace("{SCRIPT_FILES_SECTION}", script_files_section)
        .replace("{STRATEGY_FILES_SECTION}", strategy_files_section)
        .replace("{TRADING_PLAN_OUTPUT}", trading_plan_output)
        .replace("{CANDIDATES_OUTPUT}", candidates_output)
    )

    # 附加文件
    attached_files = [review_path]
    attached_files.extend(dr_files)
    attached_files.extend(_collect_existing_files(data_dir, _SCRIPT_OUTPUT_FILES))
    attached_files.extend(strategy_files)

    # 对 plan 任务，输出有两个文件，用 trading_plan.md 作为主输出检测
    success = _run_opencode(
        prompt=prompt,
        output_path=trading_plan_output,
        title="交易计划生成",
        attached_files=attached_files,
        model=model,
        timeout=timeout,
    )

    if success:
        # 强校验双文件都已生成
        if os.path.exists(candidates_output):
            size_kb = os.path.getsize(candidates_output) / 1024
            logger.info("candidates.json 已生成 (%.1f KB)", size_kb)
        else:
            logger.error(
                "trading_plan.md 已生成，但 candidates.json 缺失——"
                "视为 plan 失败，后续 risk_check/decision_logger 无法执行"
            )
            return False

    return success


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


# ── 主逻辑 ────────────────────────────────────────────


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="运行子代理分析（新闻情绪、社交情绪、复盘报告、交易计划、个股深研）"
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="数据根目录（如 ~/.ashare-assistant/data/2026-02-24）",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        choices=["news", "social", "review", "plan", "stock", "all"],
        default=["all"],
        help="要运行的任务（默认 all = news + social + review + plan）",
    )
    parser.add_argument(
        "--stock-code",
        help="股票代码（stock 任务必需）",
    )
    parser.add_argument(
        "--stock-name",
        help="股票名称（stock 任务必需）",
    )
    parser.add_argument(
        "--stock-context",
        default="",
        help="选股上下文信息",
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
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[analysis] %(message)s",
    )

    data_dir = os.path.expanduser(args.data_dir)

    # 检查 filtered/ 目录
    filtered_dir = os.path.join(data_dir, "filtered")
    if not os.path.exists(filtered_dir):
        logger.error(
            "filtered/ 目录不存在: %s\n请先运行 filter_to_markdown.py", filtered_dir
        )
        sys.exit(1)

    tasks = args.tasks
    if "all" in tasks:
        tasks = ["news", "social", "review", "plan"]

    results: dict[str, bool] = {}
    start_time = time.time()

    for task in tasks:
        task_model = _get_model(task, args.model)
        task_timeout = _get_timeout(task, args.timeout)

        logger.info("任务 [%s] 使用模型: %s, 超时: %ds", task, task_model, task_timeout)

        if task == "news":
            results["news"] = run_news_sentiment(
                data_dir, model=task_model, timeout=task_timeout
            )
        elif task == "social":
            results["social"] = run_social_sentiment(
                data_dir, model=task_model, timeout=task_timeout
            )
        elif task == "review":
            results["review"] = run_market_review(
                data_dir, model=task_model, timeout=task_timeout
            )
        elif task == "plan":
            # plan 依赖 review 成功，如果 review 在本次运行中失败则阻断
            if results.get("review") is False:
                logger.error("review 任务失败，跳过 plan 任务（依赖流水线阻断）")
                results["plan"] = False
            else:
                results["plan"] = run_trading_plan(
                    data_dir, model=task_model, timeout=task_timeout
                )
        elif task == "stock":
            if not args.stock_code or not args.stock_name:
                logger.error("stock 任务需要 --stock-code 和 --stock-name 参数")
                sys.exit(1)
            results[f"stock_{args.stock_code}"] = run_stock_deep_research(
                data_dir,
                stock_code=args.stock_code,
                stock_name=args.stock_name,
                context=args.stock_context,
                model=task_model,
                timeout=task_timeout,
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
