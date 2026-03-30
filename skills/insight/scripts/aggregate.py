"""确定性代码聚合层。

纯 Python 实现，不调用 LLM，不访问 SQLite。
输入：Memory 列表（来自 store.list_memories()）
输出：AggregateResult（统计 JSON）
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from scripts.models import Memory, MemoryKind, Scope


@dataclass
class KindStats:
    """某个 MemoryKind 的聚合统计。"""

    count: int = 0
    avg_confidence: float = 0.0
    recent_7d: int = 0
    recent_30d: int = 0
    top_scopes: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class AggregateResult:
    """聚合结果。"""

    total_memories: int = 0
    time_range: tuple[datetime, datetime] | None = None
    by_kind: dict[MemoryKind, KindStats] = field(default_factory=dict)
    by_scope: dict[Scope, int] = field(default_factory=dict)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    samples_by_kind: dict[MemoryKind, list[str]] = field(default_factory=dict)


def aggregate(memories: list[Memory]) -> AggregateResult:
    """对 Memory 列表进行确定性聚合统计。

    Args:
        memories: Memory 对象列表。

    Returns:
        AggregateResult 包含按 kind/scope/tag 的统计和样本。
    """
    if not memories:
        return AggregateResult()

    now = datetime.now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # --- time_range ---
    earliest = min(m.created_at for m in memories)
    latest = max(m.created_at for m in memories)

    # --- by_kind ---
    kind_groups: dict[MemoryKind, list[Memory]] = {}
    for m in memories:
        kind_groups.setdefault(m.kind, []).append(m)

    by_kind: dict[MemoryKind, KindStats] = {}
    for kind, group in kind_groups.items():
        count = len(group)
        avg_conf = sum(m.confidence for m in group) / count
        recent_7d = sum(1 for m in group if m.created_at >= cutoff_7d)
        recent_30d = sum(1 for m in group if m.created_at >= cutoff_30d)

        scope_counter: Counter[str] = Counter()
        for m in group:
            scope_counter[m.scope.value] += 1
        top_scopes = scope_counter.most_common(5)

        by_kind[kind] = KindStats(
            count=count,
            avg_confidence=avg_conf,
            recent_7d=recent_7d,
            recent_30d=recent_30d,
            top_scopes=top_scopes,
        )

    # --- by_scope ---
    scope_counter_all: Counter[Scope] = Counter()
    for m in memories:
        scope_counter_all[m.scope] += 1
    by_scope = dict(scope_counter_all)

    # --- top_tags ---
    tag_counter: Counter[str] = Counter()
    for m in memories:
        for tag in m.tags:
            tag_counter[tag] += 1
    top_tags = tag_counter.most_common(20)

    # --- samples_by_kind ---
    samples_by_kind: dict[MemoryKind, list[str]] = {}
    for kind, group in kind_groups.items():
        sorted_group = sorted(group, key=lambda m: m.confidence, reverse=True)
        samples_by_kind[kind] = [m.summary for m in sorted_group[:5]]

    return AggregateResult(
        total_memories=len(memories),
        time_range=(earliest, latest),
        by_kind=by_kind,
        by_scope=by_scope,
        top_tags=top_tags,
        samples_by_kind=samples_by_kind,
    )
