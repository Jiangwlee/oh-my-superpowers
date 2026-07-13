"""Runtime backend selection for `omp container` — docker compose vs apple/container.

No real docker/container binaries are exercised: `shutil.which` and
`subprocess.run` are monkeypatched. Covers backend pick order, the apple
backend's argv mapping for the browser container, and the unsupported-name
guard.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MAIN_PATH = Path(__file__).resolve().parents[3] / "cli" / "container" / "main.py"


def _load_main():
    spec = importlib.util.spec_from_file_location("container_main", _MAIN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


main = _load_main()


# --- backend selection --------------------------------------------------------

def test_runtime_prefers_docker(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda b: "/usr/bin/" + b)
    assert main._runtime() == "docker"


def test_runtime_falls_back_to_apple(monkeypatch):
    monkeypatch.setattr(
        main.shutil, "which", lambda b: "/usr/local/bin/container" if b == "container" else None
    )
    assert main._runtime() == "apple"


def test_runtime_neither_exits(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda b: None)
    with pytest.raises(main.typer.Exit) as exc:
        main._runtime()
    assert exc.value.exit_code == 4


# --- apple backend argv mapping -------------------------------------------------

class _Recorder:
    def __init__(self, returncode: int = 0):
        self.calls: list[list[str]] = []
        self.returncode = returncode

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))

        class _R:
            returncode = self.returncode
            stdout = ""
            stderr = ""

        return _R()


def _patch_apple(monkeypatch, recorder):
    monkeypatch.setattr(
        main.shutil, "which", lambda b: "/usr/local/bin/container" if b == "container" else None
    )
    monkeypatch.setattr(main.subprocess, "run", recorder)
    monkeypatch.setattr(main.Path, "is_dir", lambda self: True)


def test_apple_up_builds_volume_and_runs(monkeypatch):
    rec = _Recorder()
    _patch_apple(monkeypatch, rec)
    payload = main._apple_lifecycle("browser", "up", build=True)
    assert payload["status"] == "ok"
    flat = ["\x00".join(c) for c in rec.calls]
    assert any(c.startswith("container\x00build") for c in flat)
    assert ["container", "volume", "create", "omp-browser-profile"] in rec.calls
    run_argv = next(c for c in rec.calls if c[:2] == ["container", "run"])
    joined = " ".join(run_argv)
    assert "--shm-size 1g" in joined
    assert "-v omp-browser-profile:/data/profile" in joined
    assert "--tmpfs /data/downloads" in joined
    assert "127.0.0.1:8080:8080" in joined
    assert "127.0.0.1:6081:6081" in joined
    assert run_argv[-1] == "omp-browser-container:local"


def test_apple_up_respects_port_env(monkeypatch):
    rec = _Recorder()
    _patch_apple(monkeypatch, rec)
    monkeypatch.setenv("REST_PORT", "18080")
    monkeypatch.setenv("BIND_ADDR", "100.64.0.7")
    payload = main._apple_lifecycle("browser", "up", build=False)
    assert payload["status"] == "ok"
    run_argv = next(c for c in rec.calls if c[:2] == ["container", "run"])
    assert "100.64.0.7:18080:8080" in " ".join(run_argv)
    assert not any(c[:2] == ["container", "build"] for c in rec.calls)


def test_apple_down_stops_and_removes(monkeypatch):
    rec = _Recorder()
    _patch_apple(monkeypatch, rec)
    payload = main._apple_lifecycle("browser", "down")
    assert payload["status"] == "ok"
    assert ["container", "stop", "omp-browser"] in rec.calls
    assert ["container", "rm", "omp-browser"] in rec.calls


def test_apple_rejects_unsupported_name(monkeypatch):
    rec = _Recorder()
    _patch_apple(monkeypatch, rec)
    with pytest.raises(main.typer.Exit) as exc:
        main._apple_lifecycle("html-serve", "up")
    assert exc.value.exit_code == 2
    assert rec.calls == []
