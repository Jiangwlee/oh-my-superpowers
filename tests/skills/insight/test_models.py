"""T1 测试：models.py 核心数据模型验证。"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "insight"))

from scripts.models import (
    Insight,
    Memory,
    MemoryKind,
    Scope,
    generate_id,
)


# ---------------------------------------------------------------------------
# generate_id
# ---------------------------------------------------------------------------


class TestGenerateId:
    """generate_id(prefix) 测试。"""

    def test_mem_prefix(self):
        id_ = generate_id("mem")
        assert id_.startswith("mem_")

    def test_ins_prefix(self):
        id_ = generate_id("ins")
        assert id_.startswith("ins_")

    def test_format_matches_pattern(self):
        """格式应为 {prefix}_{hex_ts}_{hex8}。"""
        id_ = generate_id("mem")
        # prefix_hexts_hex8: hex_ts 为毫秒级十六进制时间戳，hex8 为8位随机
        pattern = r"^mem_[0-9a-f]+_[0-9a-f]{8}$"
        assert re.match(pattern, id_), f"ID '{id_}' 不匹配格式"

    def test_ins_format_matches_pattern(self):
        id_ = generate_id("ins")
        pattern = r"^ins_[0-9a-f]+_[0-9a-f]{8}$"
        assert re.match(pattern, id_), f"ID '{id_}' 不匹配格式"

    def test_two_calls_not_equal(self):
        """两次调用应生成不同 ID（随机 rand4 部分保证碰撞极低）。"""
        ids = {generate_id("mem") for _ in range(20)}
        # 20 次调用中至少有 2 个不同值
        assert len(ids) > 1

    def test_custom_prefix(self):
        id_ = generate_id("foo")
        assert id_.startswith("foo_")


# ---------------------------------------------------------------------------
# MemoryKind / Scope 枚举
# ---------------------------------------------------------------------------


class TestEnums:
    """枚举值基础测试。"""

    def test_memory_kind_values_are_strings(self):
        for kind in MemoryKind:
            assert isinstance(kind.value, str)

    def test_memory_kind_all_values_accessible(self):
        assert MemoryKind.CORRECTION == "correction"
        assert MemoryKind.PREFERENCE == "preference"
        assert MemoryKind.WORKFLOW == "workflow"
        assert MemoryKind.DECISION == "decision"
        assert MemoryKind.FACT == "fact"

    def test_scope_values_are_strings(self):
        for scope in Scope:
            assert isinstance(scope.value, str)

    def test_scope_all_values_accessible(self):
        assert Scope.PROJECT == "project"
        assert Scope.USER == "user"


# ---------------------------------------------------------------------------
# Memory 往返测试
# ---------------------------------------------------------------------------


def _make_memory(**kwargs) -> Memory:
    """构建测试用 Memory，字段可被 kwargs 覆盖。"""
    defaults = dict(
        id=generate_id("mem"),
        kind=MemoryKind.PREFERENCE,
        content="用户偏好 4 空格缩进",
        context="首次 review 代码时发现",
        scope=Scope.PROJECT,
        source_session_id="sess_abc123",
        created_at=datetime(2026, 3, 27, 10, 0, 0),
        hit_count=3,
        confidence=0.8,
        tags=["python", "style"],
    )
    defaults.update(kwargs)
    return Memory(**defaults)


class TestMemoryRoundtrip:
    """Memory.to_markdown() / Memory.from_frontmatter() 往返测试。"""

    def test_basic_roundtrip(self):
        original = _make_memory()
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)

        assert restored.id == original.id
        assert restored.kind == original.kind
        assert restored.content == original.content
        assert restored.context == original.context
        assert restored.scope == original.scope
        assert restored.source_session_id == original.source_session_id
        assert restored.hit_count == original.hit_count
        assert restored.confidence == original.confidence
        assert restored.tags == original.tags

    def test_created_at_roundtrip(self):
        original = _make_memory()
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.created_at == original.created_at

    def test_tags_empty_list(self):
        original = _make_memory(tags=[])
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.tags == []

    def test_tags_multiple(self):
        original = _make_memory(tags=["a", "b", "c"])
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.tags == ["a", "b", "c"]

    def test_content_with_colon(self):
        """content 含冒号时应正确序列化/反序列化。"""
        original = _make_memory(content="key: value 格式")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.content == "key: value 格式"

    def test_content_with_double_quotes(self):
        """content 含双引号时应正确序列化/反序列化。"""
        original = _make_memory(content='他说 "不要这样"')
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.content == '他说 "不要这样"'

    def test_content_with_chinese(self):
        """中文 content 应正确序列化/反序列化。"""
        original = _make_memory(content="用户偏好中文注释，禁止英文")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.content == "用户偏好中文注释，禁止英文"

    def test_context_with_special_chars(self):
        """context 含特殊字符时应正确序列化。"""
        original = _make_memory(context="路径: /home/user & project{foo}")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.context == "路径: /home/user & project{foo}"

    def test_memory_kind_serialization(self):
        """所有 MemoryKind 枚举值都应正确序列化。"""
        for kind in MemoryKind:
            original = _make_memory(kind=kind)
            md = original.to_markdown()
            restored = Memory.from_frontmatter(md)
            assert restored.kind == kind

    def test_scope_serialization(self):
        """所有 Scope 枚举值都应正确序列化。"""
        for scope in Scope:
            original = _make_memory(scope=scope)
            md = original.to_markdown()
            restored = Memory.from_frontmatter(md)
            assert restored.scope == scope

    def test_markdown_starts_with_frontmatter(self):
        mem = _make_memory()
        md = mem.to_markdown()
        assert md.startswith("---\n")

    def test_from_frontmatter_missing_header_raises(self):
        with pytest.raises(ValueError, match="missing frontmatter"):
            Memory.from_frontmatter("no frontmatter here")

    def test_confidence_float_precision(self):
        original = _make_memory(confidence=0.75)
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert abs(restored.confidence - 0.75) < 1e-9

    def test_hit_count_zero(self):
        original = _make_memory(hit_count=0)
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.hit_count == 0

    def test_hit_count_large(self):
        original = _make_memory(hit_count=9999)
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.hit_count == 9999

    def test_content_with_newline(self):
        """含换行符的内容应正确 roundtrip。"""
        original = _make_memory(content="line1\nline2\nline3")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.content == "line1\nline2\nline3"

    def test_content_with_backslash(self):
        """含反斜杠的内容应正确 roundtrip。"""
        original = _make_memory(context="C:\\Users\\foo\\bar")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.context == "C:\\Users\\foo\\bar"

    def test_content_with_triple_dash(self):
        """含 --- 的内容不应截断 frontmatter。"""
        original = _make_memory(content="before --- after")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.content == "before --- after"

    def test_content_with_tab(self):
        """含制表符的内容应正确 roundtrip。"""
        original = _make_memory(content="col1\tcol2")
        md = original.to_markdown()
        restored = Memory.from_frontmatter(md)
        assert restored.content == "col1\tcol2"


# ---------------------------------------------------------------------------
# Insight 往返测试
# ---------------------------------------------------------------------------


def _make_insight(**kwargs) -> Insight:
    """构建测试用 Insight，字段可被 kwargs 覆盖。"""
    defaults = dict(
        id=generate_id("ins"),
        pattern="用户偏好严格类型注解",
        action="始终使用 Python 3.10+ 联合类型语法",
        evidence=["mem_abc_0001", "mem_def_0002"],
        scope=Scope.PROJECT,
        created_at=datetime(2026, 3, 27, 10, 0, 0),
        last_validated_at=datetime(2026, 3, 27, 12, 0, 0),
        evidence_count=2,
        confidence=0.9,
        tags=["python", "types"],
    )
    defaults.update(kwargs)
    return Insight(**defaults)


class TestInsightRoundtrip:
    """Insight.to_markdown() / Insight.from_frontmatter() 往返测试。"""

    def test_basic_roundtrip(self):
        original = _make_insight()
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)

        assert restored.id == original.id
        assert restored.pattern == original.pattern
        assert restored.action == original.action
        assert restored.evidence == original.evidence
        assert restored.scope == original.scope
        assert restored.evidence_count == original.evidence_count
        assert restored.confidence == original.confidence
        assert restored.tags == original.tags

    def test_created_at_roundtrip(self):
        original = _make_insight()
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.created_at == original.created_at

    def test_last_validated_at_roundtrip(self):
        original = _make_insight()
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.last_validated_at == original.last_validated_at

    def test_evidence_empty_list(self):
        original = _make_insight(evidence=[])
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.evidence == []

    def test_evidence_multiple_ids(self):
        ids = ["mem_aaa_0001", "mem_bbb_0002", "mem_ccc_0003"]
        original = _make_insight(evidence=ids)
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.evidence == ids

    def test_pattern_with_colon(self):
        original = _make_insight(pattern="format: 始终用黑体")
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.pattern == "format: 始终用黑体"

    def test_action_with_quotes(self):
        original = _make_insight(action='使用 "strict" 模式')
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.action == '使用 "strict" 模式'

    def test_tags_empty(self):
        original = _make_insight(tags=[])
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.tags == []

    def test_scope_user(self):
        original = _make_insight(scope=Scope.USER)
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert restored.scope == Scope.USER

    def test_from_frontmatter_missing_header_raises(self):
        with pytest.raises(ValueError, match="missing frontmatter"):
            Insight.from_frontmatter("plain text, no frontmatter")

    def test_markdown_starts_with_frontmatter(self):
        ins = _make_insight()
        md = ins.to_markdown()
        assert md.startswith("---\n")

    def test_confidence_zero(self):
        original = _make_insight(confidence=0.0)
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert abs(restored.confidence - 0.0) < 1e-9

    def test_confidence_one(self):
        original = _make_insight(confidence=1.0)
        md = original.to_markdown()
        restored = Insight.from_frontmatter(md)
        assert abs(restored.confidence - 1.0) < 1e-9
