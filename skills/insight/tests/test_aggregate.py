"""T1 测试：确定性聚合层 aggregate.py 验证。"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aggregate import AggregateResult, KindStats, aggregate
from scripts.models import Memory, MemoryKind, Scope


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_COUNTER = 0


def _make_memory(
    *,
    kind: MemoryKind = MemoryKind.OTHER,
    scope: Scope = Scope.PROJECT,
    summary: str = "test memory",
    confidence: float = 0.5,
    tags: list[str] | None = None,
    created_at: datetime | None = None,
) -> Memory:
    """构造测试用 Memory 对象。"""
    global _COUNTER
    _COUNTER += 1
    return Memory(
        id=f"mem_test_{_COUNTER:04d}",
        kind=kind,
        summary=summary,
        scope=scope,
        source="test_session@claude",
        evidence_ref="test://evidence",
        created_at=created_at or datetime.now(),
        confidence=confidence,
        tags=tags or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAggregateByKind:
    """按 kind 聚合统计。"""

    def test_aggregate_by_kind(self) -> None:
        now = datetime.now()
        memories = [
            _make_memory(kind=MemoryKind.BUG, confidence=0.8, created_at=now - timedelta(days=2)),
            _make_memory(kind=MemoryKind.BUG, confidence=0.6, created_at=now - timedelta(days=10)),
            _make_memory(kind=MemoryKind.DECISION, confidence=0.9, created_at=now - timedelta(days=1)),
            _make_memory(kind=MemoryKind.DECISION, confidence=0.7, created_at=now - timedelta(days=3)),
            _make_memory(kind=MemoryKind.PATTERN, confidence=0.5, created_at=now - timedelta(days=5)),
        ]

        result = aggregate(memories)

        assert result.total_memories == 5

        # bug: count=2, avg_confidence=(0.8+0.6)/2=0.7
        bug_stats = result.by_kind[MemoryKind.BUG]
        assert bug_stats.count == 2
        assert abs(bug_stats.avg_confidence - 0.7) < 1e-6
        # recent_7d: only the one at day=2 is within 7 days
        assert bug_stats.recent_7d == 1

        # decision: count=2
        decision_stats = result.by_kind[MemoryKind.DECISION]
        assert decision_stats.count == 2
        assert abs(decision_stats.avg_confidence - 0.8) < 1e-6
        assert decision_stats.recent_7d == 2

        # pattern: count=1
        pattern_stats = result.by_kind[MemoryKind.PATTERN]
        assert pattern_stats.count == 1
        assert pattern_stats.recent_7d == 1


class TestAggregateByScope:
    """按 scope 聚合统计。"""

    def test_aggregate_by_scope(self) -> None:
        memories = [
            _make_memory(scope=Scope.FILE),
            _make_memory(scope=Scope.FILE),
            _make_memory(scope=Scope.MODULE),
            _make_memory(scope=Scope.PROJECT),
        ]

        result = aggregate(memories)

        assert result.by_scope[Scope.FILE] == 2
        assert result.by_scope[Scope.MODULE] == 1
        assert result.by_scope[Scope.PROJECT] == 1


class TestAggregateTopTags:
    """标签频率统计。"""

    def test_aggregate_top_tags(self) -> None:
        memories = [
            _make_memory(tags=["python", "bug"]),
            _make_memory(tags=["python", "refactor"]),
            _make_memory(tags=["python"]),
            _make_memory(tags=["bug"]),
            _make_memory(tags=["rust"]),
        ]

        result = aggregate(memories)

        # python appears 3 times, bug 2 times, refactor 1, rust 1
        assert len(result.top_tags) >= 4
        assert result.top_tags[0] == ("python", 3)
        assert result.top_tags[1] == ("bug", 2)
        # remaining order among ties is not guaranteed, just check they exist
        remaining = {tag for tag, _ in result.top_tags[2:]}
        assert "refactor" in remaining
        assert "rust" in remaining


class TestAggregateSamples:
    """samples_by_kind 每种最多 5 条。"""

    def test_aggregate_samples(self) -> None:
        # Create 7 bug memories with varying confidence
        memories = [
            _make_memory(
                kind=MemoryKind.BUG,
                summary=f"bug {i}",
                confidence=0.1 * i,
            )
            for i in range(1, 8)
        ]

        result = aggregate(memories)

        bug_samples = result.samples_by_kind[MemoryKind.BUG]
        assert len(bug_samples) == 5
        # Sorted by confidence descending, so first should be "bug 7"
        assert bug_samples[0] == "bug 7"
        assert bug_samples[1] == "bug 6"


class TestAggregateEmpty:
    """空列表不报错。"""

    def test_aggregate_empty(self) -> None:
        result = aggregate([])

        assert result.total_memories == 0
        assert result.by_kind == {}
        assert result.by_scope == {}
        assert result.top_tags == []
        assert result.samples_by_kind == {}
        assert result.time_range is None


class TestAggregateTimeRange:
    """time_range 取最早和最晚的 created_at。"""

    def test_aggregate_time_range(self) -> None:
        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 15, 12, 0, 0)
        t3 = datetime(2026, 2, 1, 8, 0, 0)

        memories = [
            _make_memory(created_at=t2),
            _make_memory(created_at=t1),
            _make_memory(created_at=t3),
        ]

        result = aggregate(memories)

        assert result.time_range is not None
        assert result.time_range[0] == t1
        assert result.time_range[1] == t3
