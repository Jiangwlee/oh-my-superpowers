"""End-to-end smoke tests against real tmux.

We monkey-patch `build_runtime_command` to use shell `printf` instead of a
real LLM runtime, so the tests run in milliseconds without network calls.
"""

from __future__ import annotations

import json
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
    """Replace runtime command with a fast 'cat | sh' equivalent that exits 0."""

    def fake_build(runtime, *, prompt_file, model=None):
        # Echo the prompt-file content + a runtime tag to stdout.
        # core.spawn wraps this with `set -o pipefail` + tee, so exit code propagates.
        return f"sh -c 'cat {prompt_file}; printf \"\\n[fake-{runtime}]\\n\"'"

    monkeypatch.setattr(core, "build_runtime_command", fake_build)


@pytest.fixture
def cleanup_sessions():
    created: list[str] = []
    yield created
    for sid in created:
        dispatch.kill(sid)


def test_run_returns_completed(tmp_path, cleanup_sessions):
    result = dispatch.run("claude", prompt="hello world", cwd=str(tmp_path), timeout=30)
    cleanup_sessions.append(result.session_id)
    assert result.status == "completed"
    assert result.exit_code == 0
    assert "hello world" in result.output
    assert "[fake-claude]" in result.output


def test_spawn_then_wait(tmp_path, cleanup_sessions):
    handle = dispatch.spawn("codex", prompt="ping", cwd=str(tmp_path), session_name="e2e-spawn")
    cleanup_sessions.append(handle.session_id)
    assert handle.session_id == "omp-e2e-spawn"

    result = dispatch.wait(handle, timeout=30)
    assert result.status == "completed"
    assert result.exit_code == 0
    assert "ping" in result.output


def test_spawn_with_prompt_file(tmp_path, cleanup_sessions):
    pf = tmp_path / "prompt.md"
    pf.write_text("from-file")
    handle = dispatch.spawn("pi", prompt_file=str(pf), cwd=str(tmp_path))
    cleanup_sessions.append(handle.session_id)
    result = dispatch.wait(handle, timeout=30)
    assert "from-file" in result.output
    assert result.exit_code == 0


def test_status_lists_active(tmp_path, cleanup_sessions):
    handle = dispatch.spawn("claude", prompt="x", cwd=str(tmp_path), session_name="status-probe")
    cleanup_sessions.append(handle.session_id)
    sessions = {s.session_id for s in dispatch.status()}
    assert isinstance(sessions, set)
    dispatch.wait(handle, timeout=30)


def test_kill_running_session(tmp_path, cleanup_sessions, monkeypatch):
    def slow_build(runtime, *, prompt_file, model=None):
        return "sh -c 'sleep 30'"

    monkeypatch.setattr(core, "build_runtime_command", slow_build)

    handle = dispatch.spawn("claude", prompt="x", cwd=str(tmp_path), session_name="kill-probe")
    cleanup_sessions.append(handle.session_id)
    time.sleep(0.5)
    assert tmux.has_session(handle.session_id)
    assert dispatch.kill(handle.session_id) is True
    time.sleep(0.3)
    assert not tmux.has_session(handle.session_id)


def test_session_name_collision_raises(tmp_path, cleanup_sessions, monkeypatch):
    def slow_build(runtime, *, prompt_file, model=None):
        return "sh -c 'sleep 5'"

    monkeypatch.setattr(core, "build_runtime_command", slow_build)

    handle = dispatch.spawn("claude", prompt="x", cwd=str(tmp_path), session_name="dup")
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


# ── Exit code propagation (P1 fix #1) ──────────────────────────────────────


def test_worker_failure_propagates_exit_code(tmp_path, cleanup_sessions, monkeypatch):
    """Worker that exits non-zero must surface as status='error' with exit_code."""

    def failing_build(runtime, *, prompt_file, model=None):
        return "sh -c 'echo failing; exit 7'"

    monkeypatch.setattr(core, "build_runtime_command", failing_build)

    result = dispatch.run("claude", prompt="x", cwd=str(tmp_path), timeout=30)
    cleanup_sessions.append(result.session_id)
    assert result.status == "error"
    assert result.exit_code == 7
    assert "failing" in result.output


def test_worker_success_exit_code_zero(tmp_path, cleanup_sessions):
    result = dispatch.run("claude", prompt="x", cwd=str(tmp_path), timeout=30)
    cleanup_sessions.append(result.session_id)
    assert result.exit_code == 0


# ── Metadata sidecar + custom output_file (P1 fix #3) ──────────────────────


def test_spawn_writes_metadata_sidecar(tmp_path, cleanup_sessions):
    custom_output = str(tmp_path / "custom.txt")
    handle = dispatch.spawn(
        "claude",
        prompt="x",
        cwd=str(tmp_path),
        session_name="meta-test",
        output_file=custom_output,
    )
    cleanup_sessions.append(handle.session_id)

    meta = dispatch.read_metadata(handle.session_id)
    assert meta is not None
    assert meta["output_file"] == custom_output
    assert meta["runtime"] == "claude"


def test_resolve_output_file_uses_metadata(tmp_path, cleanup_sessions):
    custom_output = str(tmp_path / "custom.txt")
    handle = dispatch.spawn(
        "claude",
        prompt="x",
        cwd=str(tmp_path),
        session_name="resolve-test",
        output_file=custom_output,
    )
    cleanup_sessions.append(handle.session_id)
    assert dispatch.resolve_output_file(handle.session_id) == custom_output


def test_kill_cleans_sidecars(tmp_path, monkeypatch):
    def slow_build(runtime, *, prompt_file, model=None):
        return "sh -c 'sleep 30'"

    monkeypatch.setattr(core, "build_runtime_command", slow_build)
    handle = dispatch.spawn("claude", prompt="x", cwd=str(tmp_path), session_name="cleanup-test")
    meta_path = Path(f"/tmp/{handle.session_id}.meta.json")
    script_path = Path(f"/tmp/{handle.session_id}.cmd.sh")
    assert meta_path.exists()
    assert script_path.exists()

    dispatch.kill(handle.session_id)
    time.sleep(0.3)
    assert not meta_path.exists()
    assert not script_path.exists()


def test_wait_many_resolves_custom_output_files(tmp_path, cleanup_sessions):
    """Multi-session wait must read from each session's actual output_file."""
    custom_a = str(tmp_path / "a.txt")
    custom_b = str(tmp_path / "b.txt")
    h_a = dispatch.spawn(
        "claude", prompt="aaa", cwd=str(tmp_path), session_name="multi-a", output_file=custom_a
    )
    h_b = dispatch.spawn(
        "claude", prompt="bbb", cwd=str(tmp_path), session_name="multi-b", output_file=custom_b
    )
    cleanup_sessions.extend([h_a.session_id, h_b.session_id])

    # Resolve via metadata (mimics what cli/dispatch/main.py wait does)
    files = {
        h_a.session_id: dispatch.resolve_output_file(h_a.session_id),
        h_b.session_id: dispatch.resolve_output_file(h_b.session_id),
    }
    assert files[h_a.session_id] == custom_a
    assert files[h_b.session_id] == custom_b

    from dispatch.wait import wait_for_many

    results = wait_for_many(
        [h_a.session_id, h_b.session_id], files, mode="all", timeout=30, poll_interval=1
    )
    by_id = {r.session_id: r for r in results}
    assert "aaa" in by_id[h_a.session_id].output
    assert "bbb" in by_id[h_b.session_id].output
    assert by_id[h_a.session_id].exit_code == 0
    assert by_id[h_b.session_id].exit_code == 0
