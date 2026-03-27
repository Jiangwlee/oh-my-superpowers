#!/usr/bin/env python3
"""Insight skill CLI。

从 AI 对话中提取高质量经验洞察（behavioral delta），
替代 ECC instinct 系统。

用法：
    cli.py extract [--runtime RUNTIME] [--since DATE] [--dry-run] [--json]
    cli.py search QUERY [--scope SCOPE] [--top-k N] [--json]
    cli.py list [--scope SCOPE] [--sort FIELD] [--limit N] [--json]
    cli.py show INSIGHT_ID
    cli.py promote INSIGHT_ID
    cli.py stats [--json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# 确保 scripts 包可导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extractor import detect_correction_patterns, generate_insights
from scripts.models import Insight, InsightScope, Runtime
from scripts.project import detect_project
from scripts.readers import ClaudeReader, CodexReader, PiReader, discover_sessions
from scripts.store import InsightStore, search_all

logger = logging.getLogger(__name__)

RUNTIME_MAP = {
    "claude": Runtime.CLAUDE,
    "codex": Runtime.CODEX,
    "pi": Runtime.PI,
}

READER_MAP = {
    Runtime.CLAUDE: ClaudeReader,
    Runtime.CODEX: CodexReader,
    Runtime.PI: PiReader,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omp-insight",
        description="从 AI 对话中提取高质量经验洞察",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- extract ---
    p_extract = sub.add_parser("extract", help="从当前项目会话中提取 insight")
    p_extract.add_argument(
        "--runtime",
        choices=["claude", "codex", "pi", "all"],
        default="all",
        help="指定 runtime（默认全部）",
    )
    p_extract.add_argument("--since", help="只处理此日期之后的 session（YYYY-MM-DD）")
    p_extract.add_argument("--dry-run", action="store_true", help="仅检测纠正模式，不调用 LLM")
    p_extract.add_argument("--json", action="store_true", dest="json_output", help="JSON 格式输出")
    p_extract.add_argument("--limit", type=int, default=20, help="最多处理的 session 数")
    p_extract.add_argument("--model", default="sonnet", help="LLM 模型（默认 sonnet）")

    # --- search ---
    p_search = sub.add_parser("search", help="检索相关 insight")
    p_search.add_argument("query", help="搜索查询")
    p_search.add_argument("--scope", choices=["project", "user", "all"], default="all")
    p_search.add_argument("--top-k", type=int, default=5)
    p_search.add_argument("--json", action="store_true", dest="json_output")

    # --- list ---
    p_list = sub.add_parser("list", help="列出已有 insight")
    p_list.add_argument("--scope", choices=["project", "user"], default="project")
    p_list.add_argument("--sort", choices=["confidence", "date"], default="confidence")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true", dest="json_output")

    # --- show ---
    p_show = sub.add_parser("show", help="查看 insight 详情")
    p_show.add_argument("insight_id", help="Insight ID")

    # --- promote ---
    p_promote = sub.add_parser("promote", help="提升 insight 到 user 级")
    p_promote.add_argument("insight_id", help="Insight ID")

    # --- stats ---
    p_stats = sub.add_parser("stats", help="统计信息")
    p_stats.add_argument("--json", action="store_true", dest="json_output")

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    handlers = {
        "extract": cmd_extract,
        "search": cmd_search,
        "list": cmd_list,
        "show": cmd_show,
        "promote": cmd_promote,
        "stats": cmd_stats,
    }
    return handlers[args.command](args)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------


def cmd_extract(args: argparse.Namespace) -> int:
    """提取 insight。"""
    project = detect_project()
    print(f"项目: {project.name} ({project.id})", file=sys.stderr)

    # 解析 runtime
    if args.runtime == "all":
        runtimes = [Runtime.CLAUDE, Runtime.CODEX, Runtime.PI]
    else:
        runtimes = [RUNTIME_MAP[args.runtime]]

    # 解析 since
    since = None
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # 发现 session
    sessions = discover_sessions(
        project.root,
        runtimes=runtimes,
        since=since,
        limit=args.limit,
    )
    print(f"发现 {len(sessions)} 个 session", file=sys.stderr)

    if not sessions:
        print("没有找到会话，退出", file=sys.stderr)
        return 0

    # 逐 session 提取纠正模式
    all_trajectories = []
    for session in sessions:
        reader_cls = READER_MAP.get(session.runtime)
        if reader_cls is None:
            continue
        reader = reader_cls()
        messages = reader.read_session(session.file_path)
        trajectories = detect_correction_patterns(messages)
        if trajectories:
            all_trajectories.extend(trajectories)
            print(
                f"  [{session.runtime.value}] {session.session_id[:20]}... "
                f"→ {len(trajectories)} 个纠正模式",
                file=sys.stderr,
            )

    print(f"\n共检测到 {len(all_trajectories)} 个纠正模式", file=sys.stderr)

    if not all_trajectories:
        print("没有检测到纠正模式", file=sys.stderr)
        return 0

    # 生成 insight
    insights = generate_insights(
        all_trajectories,
        model=args.model,
        dry_run=args.dry_run,
    )
    print(f"生成了 {len(insights)} 个 insight", file=sys.stderr)

    # 存储
    store = InsightStore(project.id)
    for insight in insights:
        store.store(insight)

    # 输出
    if args.json_output:
        _print_json([_insight_to_dict(i) for i in insights])
    else:
        for i in insights:
            print(f"\n{'='*60}")
            print(f"ID: {i.id}")
            print(f"Trigger: {i.trigger[:100]}")
            print(f"Wrong: {i.wrong_default[:100]}")
            print(f"Corrected: {i.corrected_behavior[:100]}")
            print(f"Confidence: {i.confidence}")
            print(f"Tags: {i.tags}")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """检索 insight。"""
    project = detect_project()

    if args.scope == "all":
        results = search_all(args.query, project.id, args.top_k)
    elif args.scope == "user":
        store = InsightStore("global")
        results = store.search(args.query, args.top_k)
    else:
        store = InsightStore(project.id)
        results = store.search(args.query, args.top_k)

    if args.json_output:
        _print_json([_insight_to_dict(i) for i in results])
    else:
        if not results:
            print("没有找到相关 insight")
            return 0
        for i, ins in enumerate(results, 1):
            print(f"\n{i}. [{ins.id}] (conf: {ins.confidence})")
            print(f"   Trigger: {ins.trigger[:80]}")
            print(f"   Wrong: {ins.wrong_default[:80]}")
            print(f"   Correct: {ins.corrected_behavior[:80]}")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """列出 insight。"""
    project = detect_project()
    store_id = "global" if args.scope == "user" else project.id
    store = InsightStore(store_id)

    insights = store.list_insights(sort=args.sort, limit=args.limit)

    if args.json_output:
        _print_json([_insight_to_dict(i) for i in insights])
    else:
        if not insights:
            print("没有 insight")
            return 0
        for ins in insights:
            tags = ", ".join(ins.tags) if ins.tags else "-"
            print(f"  [{ins.id}] conf={ins.confidence:.2f} | {ins.trigger[:50]} | tags: {tags}")

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """查看 insight 详情。"""
    project = detect_project()

    # 先在项目级找，再在全局找
    for store_id in [project.id, "global"]:
        store = InsightStore(store_id)
        insight = store.get(args.insight_id)
        if insight:
            print(insight.to_markdown())
            return 0

    print(f"Insight {args.insight_id} 不存在", file=sys.stderr)
    return 1


def cmd_promote(args: argparse.Namespace) -> int:
    """提升 insight 作用域。"""
    project = detect_project()
    store = InsightStore(project.id)

    if store.promote(args.insight_id):
        print(f"已提升 {args.insight_id} 到 user 级")
        return 0
    else:
        print(f"提升失败：{args.insight_id} 不存在或已是 user 级", file=sys.stderr)
        return 1


def cmd_stats(args: argparse.Namespace) -> int:
    """统计信息。"""
    project = detect_project()

    project_stats = InsightStore(project.id).stats()
    global_stats = InsightStore("global").stats()

    if args.json_output:
        _print_json({"project": project_stats, "global": global_stats})
    else:
        print(f"项目: {project.name} ({project.id})")
        print(f"  Insights: {project_stats['total_insights']}")
        print(f"  平均置信度: {project_stats['avg_confidence']}")
        print(f"  消费次数: {project_stats['total_consumptions']}")
        print(f"  采用率: {project_stats['adoption_rate']}")
        print(f"  QMD: {'可用' if project_stats['qmd_available'] else '不可用（FTS5 降级）'}")
        print(f"\n全局 (user 级):")
        print(f"  Insights: {global_stats['total_insights']}")
        print(f"  平均置信度: {global_stats['avg_confidence']}")

    return 0


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _insight_to_dict(insight: Insight) -> dict:
    return {
        "id": insight.id,
        "trigger": insight.trigger,
        "wrong_default": insight.wrong_default,
        "corrected_behavior": insight.corrected_behavior,
        "tags": insight.tags,
        "confidence": insight.confidence,
        "scope": insight.scope.value,
        "correction_count": insight.correction_count,
        "first_seen": insight.first_seen.isoformat(),
        "last_confirmed": insight.last_confirmed.isoformat(),
    }


def _print_json(data: dict | list) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
