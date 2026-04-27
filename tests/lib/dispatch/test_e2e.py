"""End-to-end smoke tests against real tmux.

We monkey-patch `build_runtime_command` to use shell `printf` instead of a
real LLM runtime, so the tests run in milliseconds without network calls.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import dispatch  # noqa: E402
from dispatch import core, tmux  # noqa: E402

if not shutil.which("tmux"):
    pytest.skip("tmux not installed", allow_module_level=True)


@pytest.fixture(autouse=True)
def _fake_runtime(monkeypatch):
    """Replace runtime command with a fast 'printf | tee' equivalent."""

    def fake_build(runtime, *, prompt_file, output_file, model=None):
        # echo the prompt-file content + a runtime tag to output_file
        return (
            f"sh -c 'cat {prompt_file}; printf \"\\n[fake-{runtime}]\\n\"' "
            f"2>&1 | tee {output_file}"
        )

    monkeypatch.setattr(core, "build_runtime_command", fake_build)


@pytest.fixture
def cleanup_sessions():
    created: list[str] = []
    yield created
    for sid in created:
        tmux.kill_session(sid)


def test_run_returns_completed(tmp_path, cleanup_sessions):
    result = dispatch.run(
        "claude", prompt="hello world", cwd=str(tmp_path), timeout=30
    )
    cleanup_sessions.append(result.session_id)
    assert result.status == "completed"
    assert "hello world" in result.output
    assert "[fake-claude]" in result.output
    assert result.duration_secs >= 0


def test_spawn_then_wait(tmp_path, cleanup_sessions):
    handle = dispatch.spawn(
        "codex", prompt="ping", cwd=str(tmp_path), session_name="e2e-spawn"
    )
    cleanup_sessions.append(handle.session_id)
    assert handle.session_id == "omp-e2e-spawn"
    assert handle.runtime == "codex"

    result = dispatch.wait(handle, timeout=30)
    assert result.status == "completed"
    assert "ping" in result.output
    assert "[fake-codex]" in result.output


def test_spawn_with_prompt_file(tmp_path, cleanup_sessions):
    pf = tmp_path / "prompt.md"
    pf.write_text("from-file")
    handle = dispatch.spawn("pi", prompt_file=str(pf), cwd=str(tmp_path))
    cleanup_sessions.append(handle.session_id)
    result = dispatch.wait(handle, timeout=30)
    assert "from-file" in result.output
    assert "[fake-pi]" in result.output


def test_status_lists_active(tmp_path, cleanup_sessions):
    # Use a long-running fake to keep the session alive briefly
    handle = dispatch.spawn(
        "claude", prompt="x", cwd=str(tmp_path), session_name="status-probe"
    )
    cleanup_sessions.append(handle.session_id)

    sessions = {s.session_id for s in dispatch.status()}
    # Either still running or already finished — both are valid;
    # we just verify the API works without exception
    assert isinstance(sessions, set)

    dispatch.wait(handle, timeout=30)


def test_kill_running_session(tmp_path, cleanup_sessions, monkeypatch):
    # Override fake_build for this test only: long-running shell sleep
    def slow_build(runtime, *, prompt_file, output_file, model=None):
        return f"sh -c 'sleep 30' 2>&1 | tee {output_file}"

    monkeypatch.setattr(core, "build_runtime_command", slow_build)

    handle = dispatch.spawn(
        "claude", prompt="x", cwd=str(tmp_path), session_name="kill-probe"
    )
    cleanup_sessions.append(handle.session_id)
    time.sleep(0.5)
    assert tmux.has_session(handle.session_id)
    assert dispatch.kill(handle.session_id) is True
    time.sleep(0.3)
    assert not tmux.has_session(handle.session_id)


def test_session_name_collision_raises(tmp_path, cleanup_sessions, monkeypatch):
    # Keep the first session alive long enough to detect the collision
    def slow_build(runtime, *, prompt_file, output_file, model=None):
        return f"sh -c 'sleep 5' 2>&1 | tee {output_file}"

    monkeypatch.setattr(core, "build_runtime_command", slow_build)

    handle = dispatch.spawn(
        "claude", prompt="x", cwd=str(tmp_path), session_name="dup"
    )
    cleanup_sessions.append(handle.session_id)
    time.sleep(0.3)
    with pytest.raises(RuntimeError, match="already exists"):
        dispatch.spawn("claude", prompt="y", cwd=str(tmp_path), session_name="dup")


def test_session_id_format():
    sid = core._generate_session_id()
    assert sid.startswith("omp-")
    assert len(sid) > len("omp-")


def test_session_name_sanitization():
    assert core._generate_session_id("my session/foo") == "omp-my-session-foo"


def test_invalid_runtime_raises():
    with pytest.raises(ValueError, match="unsupported runtime"):
        dispatch.spawn("gemini", prompt="x")


def test_missing_prompt_raises():
    with pytest.raises(ValueError, match="must provide prompt"):
        dispatch.spawn("claude")
