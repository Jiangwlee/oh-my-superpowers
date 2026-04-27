"""Runtime command construction (now returns pipeline only, no tee)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from dispatch.runtime import VALID_RUNTIMES, build_runtime_command


def test_claude_no_model():
    cmd = build_runtime_command("claude", prompt_file="/tmp/p.md")
    assert cmd.startswith("cat /tmp/p.md | claude -p")
    assert "--no-session-persistence" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert "--model" not in cmd
    # Pipeline only — no tee, no output redirection
    assert "tee" not in cmd
    assert "2>&1" not in cmd


def test_claude_with_model():
    cmd = build_runtime_command("claude", prompt_file="/tmp/p.md", model="sonnet")
    assert "--model sonnet" in cmd


def test_codex_default_has_ephemeral():
    cmd = build_runtime_command("codex", prompt_file="/tmp/p.md")
    assert "--ephemeral" in cmd
    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert cmd.endswith(" -")  # codex reads stdin via final '-'


def test_codex_with_model():
    cmd = build_runtime_command("codex", prompt_file="/tmp/p.md", model="gpt-5")
    assert "-m gpt-5" in cmd


def test_pi_no_model():
    cmd = build_runtime_command("pi", prompt_file="/tmp/p.md")
    assert cmd.startswith("pi --no-session -p @/tmp/p.md")
    assert "--model" not in cmd


def test_pi_with_model():
    cmd = build_runtime_command("pi", prompt_file="/tmp/p.md", model="qwen3.5-35b")
    assert "--model qwen3.5-35b" in cmd


def test_claude_path_with_spaces_quoted():
    cmd = build_runtime_command("claude", prompt_file="/tmp/has space.md")
    assert "'/tmp/has space.md'" in cmd


def test_pi_path_with_spaces_quoted():
    cmd = build_runtime_command("pi", prompt_file="/tmp/has space.md")
    # The whole @PATH token must be quoted, not just the path
    assert "'@/tmp/has space.md'" in cmd


def test_codex_path_with_spaces_quoted():
    cmd = build_runtime_command("codex", prompt_file="/tmp/has space.md")
    assert "'/tmp/has space.md'" in cmd


def test_unsupported_runtime_raises():
    with pytest.raises(ValueError, match="unsupported runtime"):
        build_runtime_command("gemini", prompt_file="/tmp/p.md")


def test_valid_runtimes_constant():
    assert set(VALID_RUNTIMES) == {"claude", "codex", "pi"}
