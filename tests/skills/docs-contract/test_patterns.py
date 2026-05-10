"""T1 测试：scripts/patterns.py — L2 detector 与豁免解析。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.patterns import (  # noqa: E402
    DETECTORS,
    detect_code_block,
    detect_file_path,
    detect_function_name,
    detect_step_verb,
    is_exempt,
    known_labels,
    parse_exemptions,
)


# ---------------------------------------------------------------------------
# function-name
# ---------------------------------------------------------------------------


def test_function_name_detects_simple_call() -> None:
    matches = detect_function_name("调用 foo() 处理。")
    assert len(matches) == 1
    assert matches[0].snippet == "foo()"
    assert matches[0].line == 1


def test_function_name_detects_dotted_call() -> None:
    matches = detect_function_name("module.bar() 是入口")
    assert len(matches) == 1
    assert matches[0].snippet == "module.bar()"


def test_function_name_ignores_prose_e_g() -> None:
    assert detect_function_name("如 e.g. 这种缩写不应命中") == []


def test_function_name_zero_when_clean() -> None:
    assert detect_function_name("纯文本，没有任何调用形式。") == []


# ---------------------------------------------------------------------------
# file-path
# ---------------------------------------------------------------------------


def test_file_path_detects_src_path() -> None:
    matches = detect_file_path("详见 src/foo/bar.py 的实现")
    assert len(matches) == 1
    assert "src/foo/bar.py" in matches[0].snippet


def test_file_path_detects_relative_path() -> None:
    matches = detect_file_path("./scripts/run.sh 是入口")
    assert len(matches) == 1


def test_file_path_detects_path_with_line() -> None:
    matches = detect_file_path("见 cli/main.py:42")
    assert len(matches) == 1
    assert ":42" in matches[0].snippet


def test_file_path_ignores_pure_prose() -> None:
    assert detect_file_path("我们讨论一下 architecture 的设计") == []


# ---------------------------------------------------------------------------
# code-block
# ---------------------------------------------------------------------------


def test_code_block_detects_fenced_block() -> None:
    body = "前文\n```python\ndef foo():\n    pass\n```\n后文\n"
    matches = detect_code_block(body)
    assert len(matches) == 1
    assert matches[0].line == 2


def test_code_block_zero_when_no_fence() -> None:
    assert detect_code_block("纯散文。\n再来一段。") == []


def test_code_block_handles_unbalanced_fence() -> None:
    """A single unmatched fence does not produce a Match."""
    assert detect_code_block("```only-open\n内容") == []


# ---------------------------------------------------------------------------
# step-verb
# ---------------------------------------------------------------------------


def test_step_verb_detects_xian_zai() -> None:
    matches = detect_step_verb("先调入口，再写日志。")
    assert len(matches) == 1


def test_step_verb_detects_step_n() -> None:
    matches = detect_step_verb("Step 1: 初始化环境")
    assert len(matches) == 1


def test_step_verb_detects_chinese_then() -> None:
    matches = detect_step_verb("1. 然后提交 PR")
    assert len(matches) == 1


def test_step_verb_zero_when_descriptive() -> None:
    assert detect_step_verb("系统由数据层、业务层、UI 层组成。") == []


# ---------------------------------------------------------------------------
# Registry & exemptions
# ---------------------------------------------------------------------------


def test_known_labels_match_default_rules_set() -> None:
    """Pattern label set must include the four canonical labels."""
    expected = {"function-name", "file-path", "code-block", "step-verb"}
    assert expected.issubset(set(known_labels()))


def test_detectors_dict_has_callables() -> None:
    for label, fn in DETECTORS.items():
        assert callable(fn), f"{label} detector is not callable"


def test_parse_exemptions_finds_marker() -> None:
    body = (
        "para1\n\n"
        "<!-- docs-contract: allow-code-block -->\n"
        "para2 line1\n"
        "para2 line2\n"
        "\n"
        "para3\n"
    )
    ranges = parse_exemptions(body)
    assert len(ranges) == 1
    assert ranges[0].label == "code-block"
    assert ranges[0].start_line == 3
    assert ranges[0].end_line == 6  # blank line at index 5 (1-based 6)


def test_is_exempt_within_range() -> None:
    body = (
        "<!-- docs-contract: allow-function-name -->\n"
        "foo()\n"
        "bar()\n"
        "\n"
        "baz()\n"
    )
    exemptions = parse_exemptions(body)
    assert is_exempt("function-name", 2, exemptions) is True
    assert is_exempt("function-name", 5, exemptions) is False


def test_is_exempt_label_mismatch() -> None:
    body = "<!-- docs-contract: allow-function-name -->\nsrc/foo.py\n"
    exemptions = parse_exemptions(body)
    assert is_exempt("file-path", 2, exemptions) is False
