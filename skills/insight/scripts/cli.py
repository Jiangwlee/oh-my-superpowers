#!/usr/bin/env python3
"""Insight skill CLI v3。

三层 pipeline：Capture (LLM → 结构化 Memory) → Aggregate (代码) → Evaluate (LLM → Insight)。

用法：
    cli.py capture  --source <dir> [--session <id>] [--dry-run] [--model sonnet]
    cli.py recall   --source <dir> [--format json|md] [--budget 4096] [--dry-run]
    cli.py evaluate --source <dir> [--dry-run] [--prompt-file <path>]
    cli.py list     --source <dir> [--type memory|insight]
    cli.py promote  <id> [--reason <text>] [--source <dir>]
    cli.py degrade  <id> [--reason <text>] [--source <dir>]
    cli.py delete   <id> [--source <dir>]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 确保 scripts 包可导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extractor import call_llm_array, format_conversation
from scripts.models import (
    Insight,
    Memory,
    MemoryKind,
    Runtime,
    Scope,
    generate_id,
)
from scripts.project import detect_project
from scripts.readers import (
    ClaudeReader,
    CodexReader,
    OpenClawReader,
    PiReader,
    discover_sessions,
)
from scripts.store import InsightStore, _decay_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reader 映射
# ---------------------------------------------------------------------------

READER_MAP = {
    Runtime.CLAUDE: ClaudeReader,
    Runtime.CODEX: CodexReader,
    Runtime.PI: PiReader,
    Runtime.OPENCLAW: OpenClawReader,
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CAPTURE_PROMPT = """你是一位复盘分析师。请回顾以下对话，提取有价值的行为记忆（memory）。

记忆有 6 种类型：
- bug: 发现的缺陷或错误
- decision: 技术/产品决策
- pattern: 反复出现的行为模式
- friction: 摩擦点、低效环节
- workflow: 工作流程/协作方式
- other: 无法归入上述类别

影响范围：
- file: 单个文件
- module: 模块级
- skill: 技能级
- agent: Agent 级
- project: 项目级
- other: 无法归入上述类别

对话内容：
{conversation}

请以 JSON 数组格式输出，每条记忆包含：
- kind: "bug" | "decision" | "pattern" | "friction" | "workflow" | "other"
- scope: "file" | "module" | "skill" | "agent" | "project" | "other"
- summary: 人类可读短文本（不超过 100 字）
- evidence_ref: 原始证据位置（如消息序号、文件路径等）
- confidence: 置信度（0.0-1.0）
- tags: 标签列表
- is_valid: 是否有价值（true/false）

只输出 JSON 数组，不要其他文本。只保留真正有价值的记忆，不要水分。"""

EVALUATE_PROMPT = """你是一位持续改进顾问。基于以下聚合统计数据和代表性样本，提炼出高价值的 insight。

Insight 是跨 session 反复出现的模式，值得 Agent 在每个 session 开始时优先加载。
Insight 应该极少（一屏以内），只保留真正高价值的模式。

## 聚合统计

{aggregate_json}

## 代表性样本

{samples}

对每条候选 insight 输出：
- pattern: 一句话描述这个模式
- action: Agent 应该怎么做
- evidence: 支撑此 insight 的 kind 列表（如 ["bug", "friction"]）
- confidence: 置信度（0.0-1.0）
- tags: 标签列表
- is_valid: 是否值得成为 insight（true/false）

只输出 JSON 数组。极其审慎，只有真正跨 session、反复验证的模式才值得成为 insight。"""


# ---------------------------------------------------------------------------
# Store 解析
# ---------------------------------------------------------------------------


def _resolve_store(source: str | None) -> InsightStore:
    """从 --source 参数解析 InsightStore。

    Args:
        source: 项目目录路径，None 时使用当前目录。

    Returns:
        对应项目的 InsightStore 实例。

    Raises:
        SystemExit: 无法检测到项目时退出。
    """
    path = source or os.getcwd()
    project = detect_project(path)
    if not project.root:
        print(f"错误: {path} 不是有效的项目目录", file=sys.stderr)
        sys.exit(1)
    return InsightStore(project.id)


def _resolve_project_id(source: str | None) -> str:
    """从 --source 参数解析项目 ID。

    Args:
        source: 项目目录路径，None 时使用当前目录。

    Returns:
        项目 ID 字符串。

    Raises:
        SystemExit: 无法检测到项目时退出。
    """
    path = source or os.getcwd()
    project = detect_project(path)
    if not project.root:
        print(f"错误: {path} 不是有效的项目目录", file=sys.stderr)
        sys.exit(1)
    return project.id


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------


def cmd_capture(args: argparse.Namespace) -> int:
    """从对话中提取 memory。

    流程：
    1. detect_project 检测项目
    2. discover_sessions 发现 sessions
    3. 对每个 session 用 reader 读取 messages
    4. 用 LLM 分析对话提取 Memory
    5. 去重 + 存入 store

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    # --if-no-compact: 检查 PostCompact 是否已执行过
    if args.if_no_compact:
        lock_dir = Path(os.environ.get("TMPDIR", "/tmp"))
        session_env = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
        if session_env:
            lock_file = lock_dir / f"omp-insight-compact-{session_env}.lock"
            if lock_file.exists():
                print("PostCompact 已执行过，跳过 Stop 兜底 capture", file=sys.stderr)
                return 0

    path = args.source or os.getcwd()
    project = detect_project(path)
    if not project.root:
        print(f"错误: {path} 不是有效的项目目录", file=sys.stderr)
        return 1

    print(f"项目: {project.name} ({project.id})", file=sys.stderr)

    store = InsightStore(project.id)

    # 解析 --since
    since: datetime | None = None
    if args.since:
        days = int(args.since.rstrip("d"))
        since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # 发现 sessions
    sessions = discover_sessions(project.root, since=since)
    if args.session:
        sessions = [s for s in sessions if s.session_id == args.session]

    if not sessions:
        print("没有找到会话", file=sys.stderr)
        return 0

    # 过滤消息数过少的 session（按 session 总消息数初筛）
    min_msgs = args.min_messages
    if min_msgs > 0:
        before = len(sessions)
        sessions = [s for s in sessions if s.message_count >= min_msgs]
        skipped_short = before - len(sessions)
        if skipped_short > 0:
            print(
                f"跳过 {skipped_short} 个短 session（<{min_msgs} 条消息）",
                file=sys.stderr,
            )

    if not sessions:
        print("没有需要处理的会话", file=sys.stderr)
        return 0

    print(f"待处理 {len(sessions)} 个 session", file=sys.stderr)

    # 已有 memory 的 summary 集合（用于去重）
    existing_summaries: set[str] = {
        m.summary for m in store.list_memories(limit=500)
    }

    total_created = 0
    total_skipped = 0

    for session in sessions:
        reader_cls = READER_MAP.get(session.runtime)
        if reader_cls is None:
            logger.debug("No reader for runtime %s", session.runtime)
            continue

        reader = reader_cls()
        try:
            all_messages = reader.read_session(session.file_path)
        except Exception as e:
            print(
                f"  [{session.runtime.value}] {session.session_id[:20]}... "
                f"读取失败: {e}",
                file=sys.stderr,
            )
            continue

        if not all_messages:
            continue

        # 获取游标，只处理新消息
        cursor = store.get_session_cursor(session.session_id) if not args.force else -1

        # 游标越界保护：cursor 超过实际消息数（如异常写入），自动重置并告警
        if cursor >= len(all_messages):
            print(
                f"  [{session.runtime.value}] {session.session_id[:20]}... "
                f"游标越界（cursor={cursor} >= {len(all_messages)}），重置为 -1",
                file=sys.stderr,
            )
            cursor = -1

        new_messages = all_messages[cursor + 1:]

        if not new_messages:
            print(
                f"  [{session.runtime.value}] {session.session_id[:20]}... "
                f"无新消息（cursor={cursor}）",
                file=sys.stderr,
            )
            continue

        conversation = format_conversation(new_messages)
        prompt = CAPTURE_PROMPT.format(conversation=conversation)

        # 调用 LLM
        print(
            f"  [{session.runtime.value}] {session.session_id[:20]}... "
            f"({len(new_messages)} 条新消息，共 {len(all_messages)} 条) ",
            end="",
            file=sys.stderr,
            flush=True,
        )
        if args.dry_run:
            print(f"[prompt {len(prompt)} chars]", file=sys.stderr)

        items = call_llm_array(prompt, args.model)
        if not items:
            print("LLM 调用失败或无结果", file=sys.stderr)
            continue

        session_created = 0
        session_skipped = 0

        for item in items:
            if not item.get("is_valid", False):
                session_skipped += 1
                continue

            summary = item.get("summary", "")
            if summary in existing_summaries:
                session_skipped += 1
                continue

            try:
                kind = MemoryKind(item.get("kind", "other"))
            except ValueError:
                kind = MemoryKind.OTHER

            try:
                scope = Scope(item.get("scope", "project"))
            except ValueError:
                scope = Scope.PROJECT

            memory = Memory(
                id=generate_id("mem"),
                kind=kind,
                summary=summary,
                scope=scope,
                source=f"{session.session_id}@{session.runtime.value}",
                evidence_ref=item.get("evidence_ref", ""),
                created_at=datetime.now(),
                confidence=float(item.get("confidence", 0.5)),
                tags=item.get("tags", []),
            )
            if args.dry_run:
                print(f"  [+] [{kind.value}] {summary}", file=sys.stderr)
            else:
                store.store_memory(memory)
                existing_summaries.add(summary)
            session_created += 1

        if not args.dry_run:
            total_created += session_created
            total_skipped += session_skipped
            new_cursor = cursor + len(new_messages)
            store.update_session_cursor(session.session_id, new_cursor, session_created)
            print(f"+{session_created} -{session_skipped} (cursor {cursor}→{new_cursor})", file=sys.stderr)
        else:
            print(f"  [会写入 {session_created} 条，跳过 {session_skipped} 条]", file=sys.stderr)

    if args.dry_run:
        print(f"\n[dry-run] 不写入任何数据", file=sys.stderr)
    else:
        print(
            f"\n共创建 {total_created} 条 memory，跳过 {total_skipped} 条",
            file=sys.stderr,
        )
        # 标记 PostCompact 已执行（用于 --if-no-compact 判断）
        session_env = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
        if session_env and not args.if_no_compact:
            lock_dir = Path(os.environ.get("TMPDIR", "/tmp"))
            lock_file = lock_dir / f"omp-insight-compact-{session_env}.lock"
            lock_file.touch()

    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    """召回记忆和洞察。

    --dry-run 时不记录 hit_logs，手动组装输出。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    store = _resolve_store(args.source)

    if args.dry_run:
        # 手动实现 recall 逻辑，不记录 hit_logs
        used_tokens = 0
        recalled_insights: list[Insight] = []
        recalled_memories: list[Memory] = []

        all_insights = store.list_insights(sort="confidence", limit=100)
        all_insights.sort(
            key=lambda i: _decay_score(
                i.evidence_count,
                i.confidence,
                store.get_last_hit_at(i.id) or i.created_at,
            ),
            reverse=True,
        )
        for ins in all_insights:
            text = ins.to_markdown()
            tokens = len(text) // 4
            if used_tokens + tokens > args.budget:
                break
            recalled_insights.append(ins)
            used_tokens += tokens

        all_memories = store.list_memories(sort="hit_count", limit=200)
        all_memories.sort(
            key=lambda m: _decay_score(
                m.hit_count,
                m.confidence,
                store.get_last_hit_at(m.id) or m.created_at,
            ),
            reverse=True,
        )
        for mem in all_memories:
            text = mem.to_markdown()
            tokens = len(text) // 4
            if used_tokens + tokens > args.budget:
                break
            recalled_memories.append(mem)
            used_tokens += tokens

        output = store.format_recall(recalled_insights, recalled_memories, format=args.format)

        print(output)
        print(f"[dry-run] 未记录 hit_logs", file=sys.stderr)
    else:
        output = store.recall(budget=args.budget, format=args.format)

        if args.hook:
            # Hook 模式：输出 hookSpecificOutput JSON
            import json as json_mod

            # 统计召回数量
            mem_count = output.count("\n- [") if output else 0
            summary = f"[omp-insight] recalled {mem_count} memories for this project"

            hook_output = {
                "systemMessage": summary,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": output,
                },
            }
            print(json_mod.dumps(hook_output, ensure_ascii=False))
        else:
            print(output)

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """从 memory 中提炼 insight 候选。

    v3 三层 pipeline：
    1. 加载所有 memory
    2. 调用 aggregate() 生成确定性统计
    3. 将聚合结果 + 代表性样本拼入 EVALUATE_PROMPT
    4. 调用 LLM 提炼 insight

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    from scripts.aggregate import aggregate

    store = _resolve_store(args.source)
    memories = store.list_memories(sort="confidence", limit=9999)

    if not memories:
        print("没有 memory 可供评估", file=sys.stderr)
        return 0

    print(f"加载 {len(memories)} 条 memory", file=sys.stderr)

    # 确定性聚合
    agg = aggregate(memories)
    aggregate_json = _format_aggregate_json(agg)
    samples_text = _format_aggregate_samples(agg)

    # 加载 prompt 模板
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        if not prompt_path.exists():
            print(f"错误: prompt 文件不存在: {args.prompt_file}", file=sys.stderr)
            return 1
        template = prompt_path.read_text(encoding="utf-8")
    else:
        template = EVALUATE_PROMPT

    prompt = template.format(aggregate_json=aggregate_json, samples=samples_text)

    if args.dry_run:
        print(f"[dry-run] Prompt 长度: {len(prompt)}", file=sys.stderr)
        print(f"[dry-run] Memory 数量: {len(memories)}", file=sys.stderr)
        print(f"[dry-run] 聚合统计:", file=sys.stderr)
        for kind, stats in agg.by_kind.items():
            print(f"  {kind}: count={stats.count} avg_conf={stats.avg_confidence:.2f}", file=sys.stderr)
        return 0

    # 调用 LLM
    print("调用 LLM 提炼 insight...", file=sys.stderr)
    items = call_llm_array(prompt, args.model)
    if not items:
        print("LLM 调用失败或无结果", file=sys.stderr)
        return 1

    created = 0
    for item in items:
        if not item.get("is_valid", False):
            continue

        now = datetime.now()
        evidence_kinds = item.get("evidence", [])

        insight = Insight(
            id=generate_id("ins"),
            pattern=item.get("pattern", ""),
            action=item.get("action", ""),
            evidence=evidence_kinds,
            scope=Scope.PROJECT,
            created_at=now,
            last_validated_at=now,
            evidence_count=len(evidence_kinds),
            confidence=float(item.get("confidence", 0.6)),
            tags=item.get("tags", []),
        )
        store.store_insight(insight)
        created += 1
        print(
            f"  + {insight.id}: {insight.pattern[:60]}",
            file=sys.stderr,
        )

    print(f"\n共创建 {created} 条 insight", file=sys.stderr)
    return 0


def _format_aggregate_json(agg: Any) -> str:
    """将 AggregateResult 序列化为 JSON 字符串。"""
    import json as json_mod

    data = {
        "total_memories": agg.total_memories,
        "time_range": (
            [agg.time_range[0].isoformat(), agg.time_range[1].isoformat()]
            if agg.time_range else None
        ),
        "by_kind": {
            k: {
                "count": v.count,
                "avg_confidence": round(v.avg_confidence, 3),
                "recent_7d": v.recent_7d,
                "recent_30d": v.recent_30d,
                "top_scopes": v.top_scopes,
            }
            for k, v in agg.by_kind.items()
        },
        "by_scope": agg.by_scope,
        "top_tags": agg.top_tags,
    }
    return json_mod.dumps(data, ensure_ascii=False, indent=2)


def _format_aggregate_samples(agg: Any) -> str:
    """将 samples_by_kind 格式化为人类可读文本。"""
    parts: list[str] = []
    for kind, summaries in agg.samples_by_kind.items():
        parts.append(f"### {kind} (top {len(summaries)})")
        for i, s in enumerate(summaries, 1):
            parts.append(f"  {i}. {s}")
        parts.append("")
    return "\n".join(parts) if parts else "（无样本）"


def cmd_list(args: argparse.Namespace) -> int:
    """列出 memory 和/或 insight。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    store = _resolve_store(args.source)

    show_memories = args.type in (None, "memory")
    show_insights = args.type in (None, "insight")

    if show_insights:
        insights = store.list_insights(sort="confidence", limit=50)
        if insights:
            print("## Insights\n")
            for ins in insights:
                tags = ", ".join(ins.tags) if ins.tags else "-"
                print(
                    f"  [{ins.id}] conf={ins.confidence:.2f} "
                    f"| {ins.pattern[:60]} | tags: {tags}"
                )
            print()
        elif args.type == "insight":
            print("没有 insight")

    if show_memories:
        memories = store.list_memories(sort="confidence", limit=50)
        if memories:
            print("## Memories\n")
            for mem in memories:
                tags = ", ".join(mem.tags) if mem.tags else "-"
                print(
                    f"  [{mem.id}] ({mem.kind.value}) conf={mem.confidence:.2f} "
                    f"hits={mem.hit_count} | {mem.summary[:60]} | tags: {tags}"
                )
            print()
        elif args.type == "memory":
            print("没有 memory")

    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    """将 memory 提升为 insight。

    在 project store 和 global store 中查找 memory。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    project_id = _resolve_project_id(args.source)

    # 在 project store 和 global store 中查找
    for store_id in [project_id, "global"]:
        store = InsightStore(store_id)
        result = store.promote(args.id, reason=args.reason or "")
        if result is not None:
            print(f"已提升 {args.id} -> {result.id}")
            print(f"  pattern: {result.pattern}")
            print(f"  action: {result.action}")
            return 0

    print(f"错误: memory {args.id} 不存在", file=sys.stderr)
    return 1


def cmd_degrade(args: argparse.Namespace) -> int:
    """降级 insight。

    在 project store 和 global store 中查找 insight。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    project_id = _resolve_project_id(args.source)

    for store_id in [project_id, "global"]:
        store = InsightStore(store_id)
        if store.degrade(args.id, reason=args.reason or ""):
            print(f"已降级 {args.id}")
            return 0

    print(f"错误: insight {args.id} 不存在", file=sys.stderr)
    return 1


def cmd_delete(args: argparse.Namespace) -> int:
    """删除 memory 或 insight。

    根据 ID 前缀（mem_ / ins_）决定删除类型。

    Args:
        args: 命令行参数。

    Returns:
        退出码。
    """
    project_id = _resolve_project_id(args.source)
    item_id: str = args.id

    if item_id.startswith("mem_"):
        for store_id in [project_id, "global"]:
            store = InsightStore(store_id)
            if store.delete_memory(item_id):
                print(f"已删除 memory {item_id}")
                return 0
        print(f"错误: memory {item_id} 不存在", file=sys.stderr)
        return 1

    elif item_id.startswith("ins_"):
        for store_id in [project_id, "global"]:
            store = InsightStore(store_id)
            if store.delete_insight(item_id):
                print(f"已删除 insight {item_id}")
                return 0
        print(f"错误: insight {item_id} 不存在", file=sys.stderr)
        return 1

    else:
        print(
            f"错误: 无法识别 ID 类型 '{item_id}'（需要 mem_ 或 ins_ 前缀）",
            file=sys.stderr,
        )
        return 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数列表，None 时使用 sys.argv。

    Returns:
        退出码。
    """
    parser = argparse.ArgumentParser(
        prog="omp-insight",
        description="从 AI 对话中提取 Memory，提炼 Insight",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- capture ---
    p_capture = sub.add_parser("capture", help="从对话中提取 memory")
    p_capture.add_argument("--source", default=None, help="项目目录（默认当前目录）")
    p_capture.add_argument("--session", default=None, help="仅处理指定 session ID")
    p_capture.add_argument("--since", default=None, help="只处理最近 N 天的 session（如 7d）")
    p_capture.add_argument(
        "--min-messages", type=int, default=10,
        help="最少消息数，低于此值跳过（默认 10）",
    )
    p_capture.add_argument("--force", action="store_true", help="忽略已处理标记，强制重新处理")
    p_capture.add_argument("--dry-run", action="store_true", help="仅分析不写入")
    _default_model = os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini")
    p_capture.add_argument("--model", default=_default_model, help=f"LLM 模型（默认 {_default_model}）")
    p_capture.add_argument(
        "--if-no-compact", action="store_true",
        help="仅在本次会话未触发 PostCompact 时执行（Stop hook 兜底用）",
    )

    # --- recall ---
    p_recall = sub.add_parser("recall", help="召回记忆和洞察")
    p_recall.add_argument("--source", default=None, help="项目目录（默认当前目录）")
    p_recall.add_argument(
        "--format", choices=["json", "md"], default="md", help="输出格式（默认 md）"
    )
    p_recall.add_argument(
        "--budget", type=int, default=4096, help="Token 预算（默认 4096）"
    )
    p_recall.add_argument(
        "--dry-run", action="store_true", help="不记录 hit_logs"
    )
    p_recall.add_argument(
        "--hook", action="store_true", help="Hook 模式：输出 hookSpecificOutput JSON"
    )

    # --- evaluate ---
    p_evaluate = sub.add_parser("evaluate", help="从 memory 中提炼 insight")
    p_evaluate.add_argument("--source", default=None, help="项目目录（默认当前目录）")
    p_evaluate.add_argument("--dry-run", action="store_true", help="仅输出候选不写入")
    p_evaluate.add_argument(
        "--prompt-file", default=None, help="外部 prompt 模板文件"
    )
    p_evaluate.add_argument("--model", default=_default_model, help=f"LLM 模型（默认 {_default_model}）")

    # --- list ---
    p_list = sub.add_parser("list", help="列出 memory 和 insight")
    p_list.add_argument("--source", default=None, help="项目目录（默认当前目录）")
    p_list.add_argument(
        "--type", choices=["memory", "insight"], default=None,
        help="只列出指定类型（默认两者都列）",
    )

    # --- promote ---
    p_promote = sub.add_parser("promote", help="将 memory 提升为 insight")
    p_promote.add_argument("id", help="Memory ID（mem_ 前缀）")
    p_promote.add_argument("--reason", default=None, help="提升原因")
    p_promote.add_argument("--source", default=None, help="项目目录（默认当前目录）")

    # --- degrade ---
    p_degrade = sub.add_parser("degrade", help="降级 insight")
    p_degrade.add_argument("id", help="Insight ID（ins_ 前缀）")
    p_degrade.add_argument("--reason", default=None, help="降级原因")
    p_degrade.add_argument("--source", default=None, help="项目目录（默认当前目录）")

    # --- delete ---
    p_delete = sub.add_parser("delete", help="删除 memory 或 insight")
    p_delete.add_argument("id", help="ID（mem_ 或 ins_ 前缀）")
    p_delete.add_argument("--source", default=None, help="项目目录（默认当前目录）")

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    handlers = {
        "capture": cmd_capture,
        "recall": cmd_recall,
        "evaluate": cmd_evaluate,
        "list": cmd_list,
        "promote": cmd_promote,
        "degrade": cmd_degrade,
        "delete": cmd_delete,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
