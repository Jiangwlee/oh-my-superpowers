"""情绪分析预处理（news/social），在 ashare-data 阶段生成 report/*.md。"""

from __future__ import annotations

import subprocess
import time
from shutil import which
from pathlib import Path

_NEWS_FILES = [
    "news_headline.md",
    "news_daily.md",
    "news_opportunity.md",
    "news_realtime.md",
    "news_flash.md",
]

_SOCIAL_FILES = [
    "taoguba_hot.md",
    "taoguba_recommend.md",
    "taoguba_hot_discussion.md",
]

_CACHE_TTL_SEC = 6 * 60 * 60

_NEWS_TEMPLATE = """你是一位 A 股新闻分析师。请阅读以下新闻数据文件，输出一份结构化的新闻情绪摘要。\n\n## 输入文件\n\n{FILES_SECTION}\n\n请依次读取上述文件。\n\n## 分析要求\n\n### 1. 宏观政策信号\n\n从新闻中提取与宏观经济、货币政策、监管政策相关的内容：\n\n- 是否有重大政策出台或预期变化（降准/降息/财政刺激/产业政策）\n- 监管动向（IPO 节奏、退市新规、融券限制等）\n- 对 A 股大盘的潜在影响方向（利好/利空/中性）\n\n### 2. 行业/板块催化\n\n识别新闻中提到的具体行业或板块催化事件：\n\n- 哪些行业出现政策利好或技术突破\n- 哪些行业面临利空（反垄断、出口管制、产能过剩等）\n- 事件的确定性和影响力评估\n\n### 3. 市场数据提取\n\n从头条新闻中提取关键市场数据（如存在）：\n\n- 主要指数涨跌幅（沪指、深指、创业板）\n- 成交额及与近期均值对比\n- 涨跌停家数\n- 北向资金流向\n\n### 4. 新闻情绪判断\n\n综合所有新闻，给出：\n\n- 整体情绪基调：乐观 / 谨慎乐观 / 中性 / 谨慎 / 悲观\n- 情绪驱动因素（1-2 句）\n- 是否存在情绪极端化风险（一致性预期过强时需警示反向风险）\n\n### 5. 自由分析\n\n上述框架可能无法覆盖所有重要信息。请在此区域补充你认为重要但不属于以上类别的发现。\n\n## 输出格式\n\n严格按以下 Markdown 格式输出，不要添加额外章节。每个章节如无相关内容，写"无"。\n\n```markdown\n# 新闻情绪分析报告\n\n## 宏观政策信号\n\n- [政策1]：[简述内容] → 影响：[利好/利空/中性] [影响板块]\n\n## 行业催化事件\n\n| 行业/板块 | 催化事件 | 方向 | 确定性 | 新闻来源摘要 |\n|-----------|---------|------|--------|-------------|\n| [行业名] | [事件描述] | 利好/利空 | 高/中/低 | 「[新闻标题片段]」 |\n\n## 市场数据\n\n- 沪指：[X%] | 深指：[X%] | 创业板：[X%]\n\n## 情绪判断\n\n- **整体基调**：[乐观/谨慎乐观/中性/谨慎/悲观]\n\n## 关键新闻标题（Top 10）\n\n1. 「[新闻标题]」→ [正面/负面/中性] | [关联板块]\n\n## 自由分析\n\n[补充分析内容，无则写"无额外发现"]\n```\n\n## 重要约束\n\n1. 输出总长度控制在 3000 字以内\n2. 重点突出对次日交易有实际指导意义的信息\n3. 不确定的信息标注“待确认”\n"""

_SOCIAL_TEMPLATE = """你是一位 A 股社交情绪分析师。请阅读以下社交平台数据文件，输出一份结构化的社交情绪摘要。\n\n## 输入文件\n\n{FILES_SECTION}\n\n请依次读取上述文件。\n\n## 分析重点\n\n1. 热门题材与共识方向（哪些板块被反复讨论）\n2. 龙头股热度（提及度、情绪方向、分歧度）\n3. 风险信号（吹票过热、连板一致性、潜在兑现）\n4. 可交易线索（次日可验证的强弱点）\n\n## 输出格式\n\n```markdown\n# 社交情绪分析报告\n\n## 热门题材\n- [题材]：[热度描述]\n\n## 龙头股关注度\n| 代码 | 名称 | 情绪方向 | 分歧度 | 备注 |\n|------|------|---------|--------|------|\n| ... | ... | 看多/看空/分歧 | 高/中/低 | ... |\n\n## 风险信号\n- ...\n\n## 次日跟踪要点\n1. ...\n```\n\n要求：\n1. 输出总长度控制在 2500 字以内\n2. 不要粘贴原文长段落，只做提炼\n3. 无法确认的信息明确标注“待确认”\n"""


def _build_files_section(base_dir: Path, filenames: list[str]) -> tuple[str, list[str]]:
    lines: list[str] = []
    attached: list[str] = []
    for name in filenames:
        path = base_dir / name
        if path.exists():
            size_kb = path.stat().st_size / 1024
            lines.append(f"- `{path}` ({size_kb:.1f} KB)")
            attached.append(str(path))
    section = "\n".join(lines) if lines else "（无可用文件）"
    return section, attached


def _extract_markdown_from_stdout(stdout: str) -> str:
    lines = stdout.split("\n")
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[idx:]).strip()
    return ""


def _run_opencode_markdown(
    *,
    prompt: str,
    title: str,
    model: str,
    output_path: Path,
    attached_files: list[str],
    timeout_sec: int,
    overwrite: bool,
) -> tuple[bool, str]:
    if (not overwrite) and output_path.exists() and output_path.stat().st_size > 0:
        age_sec = max(0.0, time.time() - output_path.stat().st_mtime)
        if age_sec <= _CACHE_TTL_SEC:
            return True, f"cached_ttl_hit({int(age_sec)}s)"

    output_instruction = (
        "请将完整 Markdown 分析结果直接输出到 stdout，"
        "并以一级标题 `#` 开头，不要输出额外解释。"
    )
    full_prompt = f"{prompt}\n\n---\n\n{output_instruction}"

    cmd = ["opencode", "run", "--model", model, "--title", title]
    for file_path in attached_files:
        cmd.extend(["--file", file_path])

    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=max(1, timeout_sec),
            check=False,
            cwd=str(Path.home()),
        )
    except FileNotFoundError:
        return False, "opencode_not_found"
    except subprocess.TimeoutExpired:
        return False, "timeout"

    if result.returncode != 0:
        return False, (result.stderr or "opencode_failed")[:500]

    content = _extract_markdown_from_stdout(result.stdout or "")
    if not content:
        return False, "stdout_no_markdown"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return True, "ok"


def run_sentiment_preprocess(
    *,
    data_dir: Path,
    model: str = "deepseek/deepseek-chat",
    timeout_sec: int = 300,
    overwrite: bool = False,
) -> dict[str, object]:
    """执行 news/social 情绪预处理，输出 report/*.md。"""
    filtered_dir = data_dir / "filtered"
    report_dir = data_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    if which("opencode") is None:
        elapsed = round(time.time() - started, 3)
        return {
            "ok": True,
            "skipped": True,
            "elapsed_sec": elapsed,
            "news": {"ok": False, "message": "skipped_opencode_not_found"},
            "social": {"ok": False, "message": "skipped_opencode_not_found"},
            "model": model,
        }

    news_files_section, news_attached = _build_files_section(filtered_dir, _NEWS_FILES)
    news_prompt = _NEWS_TEMPLATE.replace("{FILES_SECTION}", news_files_section)
    news_ok, news_msg = _run_opencode_markdown(
        prompt=news_prompt,
        title="新闻情绪分析",
        model=model,
        output_path=report_dir / "news_sentiment.md",
        attached_files=news_attached,
        timeout_sec=timeout_sec,
        overwrite=overwrite,
    )

    social_files_section, social_attached = _build_files_section(filtered_dir, _SOCIAL_FILES)
    social_prompt = _SOCIAL_TEMPLATE.replace("{FILES_SECTION}", social_files_section)
    social_ok, social_msg = _run_opencode_markdown(
        prompt=social_prompt,
        title="社交情绪分析",
        model=model,
        output_path=report_dir / "social_sentiment.md",
        attached_files=social_attached,
        timeout_sec=timeout_sec,
        overwrite=overwrite,
    )

    elapsed = round(time.time() - started, 3)
    return {
        "ok": bool(news_ok and social_ok),
        "elapsed_sec": elapsed,
        "news": {"ok": news_ok, "message": news_msg},
        "social": {"ok": social_ok, "message": social_msg},
        "model": model,
    }
