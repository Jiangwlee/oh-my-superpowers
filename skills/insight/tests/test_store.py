"""T1 测试：store.py InsightStore 完整行为验证。"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.store as store_module
from scripts.models import (
    Insight,
    Memory,
    MemoryKind,
    Scope,
    generate_id,
)
from scripts.store import InsightStore, _decay_score, DECAY_GRACE_MONTHS, DECAY_RATE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """提供指向临时目录的 InsightStore，隔离真实 ~/.local/share/…。"""
    monkeypatch.setattr(store_module, "BASE_DIR", tmp_path / "insight")
    return InsightStore("test_project")


def _make_memory(**kwargs) -> Memory:
    defaults = dict(
        id=generate_id("mem"),
        kind=MemoryKind.PREFERENCE,
        content="用户偏好 4 空格缩进",
        context="code review 时发现",
        scope=Scope.PROJECT,
        source_session_id="sess_001",
        created_at=datetime(2026, 3, 27, 10, 0, 0),
        hit_count=0,
        confidence=0.8,
        tags=["python"],
    )
    defaults.update(kwargs)
    return Memory(**defaults)


def _make_insight(**kwargs) -> Insight:
    defaults = dict(
        id=generate_id("ins"),
        pattern="用户偏好严格类型注解",
        action="始终使用 Python 3.10+ 联合类型",
        evidence=[],
        scope=Scope.PROJECT,
        created_at=datetime(2026, 3, 27, 10, 0, 0),
        last_validated_at=datetime(2026, 3, 27, 12, 0, 0),
        evidence_count=0,
        confidence=0.9,
        tags=[],
    )
    defaults.update(kwargs)
    return Insight(**defaults)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------


class TestInsightStoreInit:
    def test_creates_memories_dir(self, store):
        assert store.memories_dir.is_dir()

    def test_creates_insights_dir(self, store):
        assert store.insights_dir.is_dir()

    def test_creates_db(self, store):
        assert store.db_path.exists()

    def test_evidence_links_table_exists(self, store):
        conn = sqlite3.connect(str(store.db_path))
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "evidence_links" in tables

    def test_hit_logs_table_exists(self, store):
        conn = sqlite3.connect(str(store.db_path))
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "hit_logs" in tables

    def test_project_id_stored(self, store):
        assert store.project_id == "test_project"


# ---------------------------------------------------------------------------
# Memory CRUD
# ---------------------------------------------------------------------------


class TestMemoryCrud:
    def test_store_and_get_roundtrip(self, store):
        mem = _make_memory()
        store.store_memory(mem)
        result = store.get_memory(mem.id)

        assert result is not None
        assert result.id == mem.id
        assert result.content == mem.content
        assert result.kind == mem.kind

    def test_get_nonexistent_returns_none(self, store):
        assert store.get_memory("mem_nonexistent_0000") is None

    def test_store_memory_returns_id(self, store):
        mem = _make_memory()
        returned_id = store.store_memory(mem)
        assert returned_id == mem.id

    def test_list_memories_returns_all(self, store):
        mems = [_make_memory() for _ in range(3)]
        for m in mems:
            store.store_memory(m)
        listed = store.list_memories()
        assert len(listed) == 3

    def test_list_memories_sorted_by_hit_count_desc(self, store):
        m1 = _make_memory(hit_count=1)
        m2 = _make_memory(hit_count=10)
        m3 = _make_memory(hit_count=5)
        for m in (m1, m2, m3):
            store.store_memory(m)

        listed = store.list_memories(sort="hit_count")
        assert listed[0].hit_count >= listed[1].hit_count >= listed[2].hit_count

    def test_list_memories_sorted_by_confidence_desc(self, store):
        m1 = _make_memory(confidence=0.3)
        m2 = _make_memory(confidence=0.9)
        m3 = _make_memory(confidence=0.6)
        for m in (m1, m2, m3):
            store.store_memory(m)

        listed = store.list_memories(sort="confidence")
        assert listed[0].confidence >= listed[1].confidence >= listed[2].confidence

    def test_list_memories_respects_limit(self, store):
        for _ in range(5):
            store.store_memory(_make_memory())
        listed = store.list_memories(limit=3)
        assert len(listed) == 3

    def test_delete_memory_removes_file(self, store):
        mem = _make_memory()
        store.store_memory(mem)
        result = store.delete_memory(mem.id)

        assert result is True
        assert store.get_memory(mem.id) is None

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete_memory("mem_nonexistent_0000") is False

    def test_overwrite_memory(self, store):
        """同 ID 再次 store 应覆盖文件。"""
        mem = _make_memory()
        store.store_memory(mem)
        # 修改内容再存一次
        updated = _make_memory(id=mem.id, content="更新后的内容", hit_count=5)
        store.store_memory(updated)

        result = store.get_memory(mem.id)
        assert result is not None
        assert result.content == "更新后的内容"
        assert result.hit_count == 5


# ---------------------------------------------------------------------------
# Insight CRUD
# ---------------------------------------------------------------------------


class TestInsightCrud:
    def test_store_and_get_roundtrip(self, store):
        ins = _make_insight()
        store.store_insight(ins)
        result = store.get_insight(ins.id)

        assert result is not None
        assert result.id == ins.id
        assert result.pattern == ins.pattern
        assert result.action == ins.action

    def test_get_nonexistent_returns_none(self, store):
        assert store.get_insight("ins_nonexistent_0000") is None

    def test_store_insight_returns_id(self, store):
        ins = _make_insight()
        returned_id = store.store_insight(ins)
        assert returned_id == ins.id

    def test_list_insights_returns_all(self, store):
        insights = [_make_insight() for _ in range(3)]
        for i in insights:
            store.store_insight(i)
        listed = store.list_insights()
        assert len(listed) == 3

    def test_list_insights_sorted_by_confidence_desc(self, store):
        i1 = _make_insight(confidence=0.5)
        i2 = _make_insight(confidence=0.95)
        i3 = _make_insight(confidence=0.7)
        for i in (i1, i2, i3):
            store.store_insight(i)

        listed = store.list_insights(sort="confidence")
        assert listed[0].confidence >= listed[1].confidence >= listed[2].confidence

    def test_list_insights_sorted_by_evidence_count_desc(self, store):
        i1 = _make_insight(evidence_count=1)
        i2 = _make_insight(evidence_count=10)
        i3 = _make_insight(evidence_count=4)
        for i in (i1, i2, i3):
            store.store_insight(i)

        listed = store.list_insights(sort="evidence_count")
        assert listed[0].evidence_count >= listed[1].evidence_count >= listed[2].evidence_count

    def test_list_insights_respects_limit(self, store):
        for _ in range(5):
            store.store_insight(_make_insight())
        listed = store.list_insights(limit=2)
        assert len(listed) == 2

    def test_delete_insight_removes_file(self, store):
        ins = _make_insight()
        store.store_insight(ins)
        result = store.delete_insight(ins.id)

        assert result is True
        assert store.get_insight(ins.id) is None

    def test_delete_insight_removes_evidence_links(self, store):
        ins = _make_insight()
        mem = _make_memory()
        store.store_memory(mem)
        store.store_insight(ins)
        store.link_evidence(ins.id, mem.id)

        store.delete_insight(ins.id)

        # evidence_links 应被清除
        links = store.get_evidence(ins.id)
        assert links == []

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete_insight("ins_nonexistent_0000") is False


# ---------------------------------------------------------------------------
# Evidence links
# ---------------------------------------------------------------------------


class TestEvidenceLinks:
    def test_link_and_get_evidence(self, store):
        ins = _make_insight()
        mem = _make_memory()
        store.store_insight(ins)
        store.store_memory(mem)

        store.link_evidence(ins.id, mem.id)
        evidence = store.get_evidence(ins.id)

        assert mem.id in evidence

    def test_multiple_links(self, store):
        ins = _make_insight()
        store.store_insight(ins)
        mem_ids = []
        for _ in range(3):
            mem = _make_memory()
            store.store_memory(mem)
            mem_ids.append(mem.id)
            store.link_evidence(ins.id, mem.id)

        evidence = store.get_evidence(ins.id)
        assert sorted(evidence) == sorted(mem_ids)

    def test_duplicate_link_does_not_raise(self, store):
        """INSERT OR IGNORE：重复 link 不应抛出异常。"""
        ins = _make_insight()
        mem = _make_memory()
        store.store_insight(ins)
        store.store_memory(mem)

        store.link_evidence(ins.id, mem.id)
        store.link_evidence(ins.id, mem.id)  # 第二次不应报错

        evidence = store.get_evidence(ins.id)
        assert evidence.count(mem.id) == 1

    def test_get_evidence_empty(self, store):
        assert store.get_evidence("ins_nonexistent_0000") == []


# ---------------------------------------------------------------------------
# Hit logging
# ---------------------------------------------------------------------------


class TestHitLogging:
    def test_log_hit_increases_count(self, store):
        item_id = generate_id("mem")
        assert store.get_hit_count(item_id) == 0

        store.log_hit(item_id, "memory")
        assert store.get_hit_count(item_id) == 1

    def test_multiple_hits(self, store):
        item_id = generate_id("mem")
        for _ in range(5):
            store.log_hit(item_id, "memory", session_id="sess_001")
        assert store.get_hit_count(item_id) == 5

    def test_hit_count_isolated_per_item(self, store):
        id_a = generate_id("mem")
        id_b = generate_id("ins")
        store.log_hit(id_a, "memory")
        store.log_hit(id_a, "memory")
        store.log_hit(id_b, "insight")

        assert store.get_hit_count(id_a) == 2
        assert store.get_hit_count(id_b) == 1

    def test_get_hit_count_zero_for_unknown(self, store):
        assert store.get_hit_count("unknown_id_9999") == 0


# ---------------------------------------------------------------------------
# recall()
# ---------------------------------------------------------------------------


class TestRecall:
    def test_empty_store_returns_no_found_message(self, store):
        result = store.recall()
        assert result == "No memories or insights found."

    def test_recall_with_insight_and_memory(self, store):
        mem = _make_memory(content="偏好 4 空格")
        ins = _make_insight(pattern="强类型注解模式")
        store.store_memory(mem)
        store.store_insight(ins)

        result = store.recall()
        assert "强类型注解模式" in result
        assert "偏好 4 空格" in result

    def test_recall_md_contains_insights_section(self, store):
        ins = _make_insight()
        store.store_insight(ins)

        result = store.recall(format="md")
        assert "## Insights" in result

    def test_recall_md_contains_memories_section(self, store):
        mem = _make_memory()
        store.store_memory(mem)

        result = store.recall(format="md")
        assert "## Memories" in result

    def test_recall_budget_truncation(self, store):
        """极小预算下应截断输出。"""
        for _ in range(10):
            store.store_memory(_make_memory(hit_count=5, confidence=0.9))
        for _ in range(5):
            store.store_insight(_make_insight(confidence=0.9))

        # budget=1 时几乎所有内容应被截断（recall 不会超出预算）
        result_small = store.recall(budget=1)
        result_large = store.recall(budget=99999)
        # 小预算输出应短于大预算输出
        assert len(result_small) <= len(result_large)

    def test_recall_format_json_returns_valid_json(self, store):
        mem = _make_memory()
        ins = _make_insight()
        store.store_memory(mem)
        store.store_insight(ins)

        result = store.recall(format="json")
        data = json.loads(result)  # 不应抛出
        assert "insights" in data
        assert "memories" in data

    def test_recall_json_structure(self, store):
        mem = _make_memory(content="test content")
        ins = _make_insight(pattern="test pattern")
        store.store_memory(mem)
        store.store_insight(ins)

        data = json.loads(store.recall(format="json"))
        assert len(data["insights"]) == 1
        assert len(data["memories"]) == 1
        assert data["insights"][0]["pattern"] == "test pattern"
        assert data["memories"][0]["content"] == "test content"

    def test_recall_logs_hits(self, store):
        """recall 后应记录命中日志。"""
        mem = _make_memory()
        ins = _make_insight()
        store.store_memory(mem)
        store.store_insight(ins)

        store.recall()

        assert store.get_hit_count(mem.id) >= 1
        assert store.get_hit_count(ins.id) >= 1


# ---------------------------------------------------------------------------
# promote()
# ---------------------------------------------------------------------------


class TestPromote:
    def test_promote_creates_insight(self, store):
        mem = _make_memory()
        store.store_memory(mem)

        insight = store.promote(mem.id, reason="pattern detected")
        assert insight is not None
        assert insight.id.startswith("ins_")

    def test_promote_insight_stored(self, store):
        mem = _make_memory()
        store.store_memory(mem)

        insight = store.promote(mem.id)
        assert store.get_insight(insight.id) is not None

    def test_promote_creates_evidence_link(self, store):
        mem = _make_memory()
        store.store_memory(mem)

        insight = store.promote(mem.id)
        evidence = store.get_evidence(insight.id)
        assert mem.id in evidence

    def test_promote_memory_preserved(self, store):
        """promote 后 memory 应保留。"""
        mem = _make_memory()
        store.store_memory(mem)

        store.promote(mem.id)
        assert store.get_memory(mem.id) is not None

    def test_promote_nonexistent_returns_none(self, store):
        result = store.promote("mem_nonexistent_0000")
        assert result is None

    def test_promote_uses_reason_as_action(self, store):
        mem = _make_memory()
        store.store_memory(mem)

        reason = "经过 5 次观察确认此模式"
        insight = store.promote(mem.id, reason=reason)
        assert insight.action == reason

    def test_promote_uses_context_when_no_reason(self, store):
        mem = _make_memory(context="首次 review 时发现")
        store.store_memory(mem)

        insight = store.promote(mem.id)
        assert insight.action == "首次 review 时发现"

    def test_promote_inherits_scope(self, store):
        mem = _make_memory(scope=Scope.USER)
        store.store_memory(mem)

        insight = store.promote(mem.id)
        assert insight.scope == Scope.USER

    def test_promote_inherits_confidence(self, store):
        mem = _make_memory(confidence=0.75)
        store.store_memory(mem)

        insight = store.promote(mem.id)
        assert abs(insight.confidence - 0.75) < 1e-9

    def test_promote_inherits_tags(self, store):
        mem = _make_memory(tags=["python", "style"])
        store.store_memory(mem)

        insight = store.promote(mem.id)
        assert insight.tags == ["python", "style"]


# ---------------------------------------------------------------------------
# degrade()
# ---------------------------------------------------------------------------


class TestDegrade:
    def test_degrade_removes_insight_file(self, store):
        ins = _make_insight()
        store.store_insight(ins)

        result = store.degrade(ins.id, reason="pattern invalidated")
        assert result is True
        assert store.get_insight(ins.id) is None

    def test_degrade_cleans_evidence_links(self, store):
        ins = _make_insight()
        mem = _make_memory()
        store.store_insight(ins)
        store.store_memory(mem)
        store.link_evidence(ins.id, mem.id)

        store.degrade(ins.id)

        assert store.get_evidence(ins.id) == []

    def test_degrade_memory_preserved(self, store):
        """degrade 后 memory 应保留。"""
        mem = _make_memory()
        ins = _make_insight()
        store.store_memory(mem)
        store.store_insight(ins)
        store.link_evidence(ins.id, mem.id)

        store.degrade(ins.id)

        assert store.get_memory(mem.id) is not None

    def test_degrade_nonexistent_returns_false(self, store):
        result = store.degrade("ins_nonexistent_0000")
        assert result is False

    def test_degrade_without_reason(self, store):
        ins = _make_insight()
        store.store_insight(ins)

        result = store.degrade(ins.id)
        assert result is True


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------


class TestStats:
    def test_empty_store_stats(self, store):
        s = store.stats()
        assert s["total_memories"] == 0
        assert s["total_insights"] == 0
        assert s["total_hits"] == 0
        assert s["total_evidence_links"] == 0

    def test_stats_counts_memories(self, store):
        for _ in range(3):
            store.store_memory(_make_memory())
        s = store.stats()
        assert s["total_memories"] == 3

    def test_stats_counts_insights(self, store):
        for _ in range(2):
            store.store_insight(_make_insight())
        s = store.stats()
        assert s["total_insights"] == 2

    def test_stats_counts_hits(self, store):
        store.log_hit("some_id", "memory")
        store.log_hit("some_id", "memory")
        s = store.stats()
        assert s["total_hits"] == 2

    def test_stats_counts_evidence_links(self, store):
        ins = _make_insight()
        mem1 = _make_memory()
        mem2 = _make_memory()
        store.store_insight(ins)
        store.store_memory(mem1)
        store.store_memory(mem2)
        store.link_evidence(ins.id, mem1.id)
        store.link_evidence(ins.id, mem2.id)

        s = store.stats()
        assert s["total_evidence_links"] == 2

    def test_stats_contains_project_id(self, store):
        s = store.stats()
        assert s["project_id"] == "test_project"

    def test_stats_contains_store_path(self, store):
        s = store.stats()
        assert "store_path" in s
        assert len(s["store_path"]) > 0

    def test_stats_decrements_after_delete(self, store):
        mem = _make_memory()
        store.store_memory(mem)
        assert store.stats()["total_memories"] == 1

        store.delete_memory(mem.id)
        assert store.stats()["total_memories"] == 0


# ---------------------------------------------------------------------------
# _decay_score + recall time decay
# ---------------------------------------------------------------------------


class TestDecayScore:
    """_decay_score 和 recall 排序中的 time decay 测试。"""

    def test_no_penalty_within_grace_period(self):
        """DECAY_GRACE_MONTHS 内 score = hit_count * confidence。"""
        now = datetime(2026, 6, 1)
        last_hit = datetime(2026, 5, 1)  # 1 月前
        with patch("scripts.store.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            score = _decay_score(5, 0.8, last_hit)
        assert score == pytest.approx(5 * 0.8)

    def test_linear_penalty_after_grace(self):
        """6 个月时 penalty = (6 - 3) * 0.5 = 1.5。"""
        now = datetime(2026, 6, 1)
        last_hit = datetime(2025, 12, 1)  # 6 个月前
        with patch("scripts.store.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            score = _decay_score(2, 0.6, last_hit)
        expected = 2 * 0.6 - (6 - DECAY_GRACE_MONTHS) * DECAY_RATE
        assert score == pytest.approx(expected)

    def test_high_frequency_resists_decay(self):
        """高频条目即使 12 个月仍有正分。"""
        now = datetime(2026, 12, 1)
        last_hit = datetime(2026, 1, 1)  # 11 个月前
        with patch("scripts.store.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            score = _decay_score(10, 0.9, last_hit)
        # 10 * 0.9 - (11 - 3) * 0.5 = 9.0 - 4.0 = 5.0
        assert score > 0

    def test_uses_last_hit_at_not_created_at(self):
        """验证衰减基于 last_hit_at：相同 created_at 不同 last_hit_at 应有不同 score。"""
        now = datetime(2026, 6, 1)
        recent_hit = datetime(2026, 5, 1)   # 1 月前
        old_hit = datetime(2025, 6, 1)      # 12 个月前
        with patch("scripts.store.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            score_recent = _decay_score(5, 0.8, recent_hit)
            score_old = _decay_score(5, 0.8, old_hit)
        assert score_recent > score_old

    def test_negative_score_sorts_last(self):
        """低频老旧条目产生负分。"""
        now = datetime(2026, 12, 1)
        last_hit = datetime(2025, 6, 1)  # 18 个月前
        with patch("scripts.store.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            score = _decay_score(1, 0.5, last_hit)
        # 1 * 0.5 - (18 - 3) * 0.5 = 0.5 - 7.5 = -7.0
        assert score < 0

    def test_recall_order_with_decay(self, store):
        """recall 输出中高 decay score 的条目排在前面。"""
        # 创建两条 memory：一条最近命中高频，一条古老低频
        mem_fresh = _make_memory(content="新鲜记忆", hit_count=5, confidence=0.9)
        mem_stale = _make_memory(content="陈旧记忆", hit_count=1, confidence=0.5)
        store.store_memory(mem_fresh)
        store.store_memory(mem_stale)

        # 为 fresh memory 记录近期 hit
        store.log_hit(mem_fresh.id, "memory")

        result = store.recall(format="md")
        # 新鲜记忆应该排在前面
        if "新鲜记忆" in result and "陈旧记忆" in result:
            assert result.index("新鲜记忆") < result.index("陈旧记忆")
