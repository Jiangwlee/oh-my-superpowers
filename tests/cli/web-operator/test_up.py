"""Bootstrap command (`omp web-operator up`) — launcher wiring and decision flow.

All cases are isolated: no real browser, no real systemctl, no production
profile. Health and launcher are injected via monkeypatch.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MAIN_PATH = (
    Path(__file__).resolve().parents[3] / "cli" / "web-operator" / "main.py"
)


def _load_main():
    spec = importlib.util.spec_from_file_location("web_operator_main", _MAIN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


main = _load_main()


# --- launcher selection -----------------------------------------------------

def test_make_launcher_systemd(monkeypatch):
    monkeypatch.setattr(main, "WEB_OPERATOR_LAUNCHER", "systemd")
    monkeypatch.setattr(main, "WEB_OPERATOR_SERVICE", "my-chrome.service")
    launcher = main._make_launcher()
    assert isinstance(launcher, main._SystemdLauncher)
    assert launcher.unit == "my-chrome.service"


def test_make_launcher_unsupported(monkeypatch):
    monkeypatch.setattr(main, "WEB_OPERATOR_LAUNCHER", "launchd")
    with pytest.raises(main.typer.BadParameter):
        main._make_launcher()


def test_systemd_launcher_argv(monkeypatch):
    calls = []
    monkeypatch.setattr(main.subprocess, "call", lambda argv: calls.append(argv) or 0)
    launcher = main._SystemdLauncher("chrome-cdp.service")
    launcher.start()
    launcher.restart()
    assert calls == [
        ["systemctl", "--user", "start", "chrome-cdp.service"],
        ["systemctl", "--user", "restart", "chrome-cdp.service"],
    ]


# --- up decision flow -------------------------------------------------------

class _SpyLauncher:
    def __init__(self):
        self.actions = []

    def start(self):
        self.actions.append("start")
        return 0

    def restart(self):
        self.actions.append("restart")
        return 0


def _patch_launcher(monkeypatch):
    spy = _SpyLauncher()
    monkeypatch.setattr(main, "_make_launcher", lambda: spy)
    return spy


def test_up_healthy_is_noop(monkeypatch):
    spy = _patch_launcher(monkeypatch)
    monkeypatch.setattr(main, "_cdp_health", lambda: True)
    with pytest.raises(main.typer.Exit) as exc:
        main._up_impl(restart=False, timeout=5)
    assert exc.value.exit_code == 0
    assert spy.actions == []  # never touched the service


def test_up_down_starts_then_ready(monkeypatch):
    spy = _patch_launcher(monkeypatch)
    health = iter([False, True])  # down on probe, ready after start
    monkeypatch.setattr(main, "_cdp_health", lambda: next(health))
    monkeypatch.setattr(main.time, "sleep", lambda _: None)
    with pytest.raises(main.typer.Exit) as exc:
        main._up_impl(restart=False, timeout=5)
    assert exc.value.exit_code == 0
    assert spy.actions == ["start"]


def test_up_restart_skips_initial_probe(monkeypatch):
    spy = _patch_launcher(monkeypatch)
    monkeypatch.setattr(main, "_cdp_health", lambda: True)
    monkeypatch.setattr(main.time, "sleep", lambda _: None)
    with pytest.raises(main.typer.Exit) as exc:
        main._up_impl(restart=True, timeout=5)
    assert exc.value.exit_code == 0
    assert spy.actions == ["restart"]


def test_up_start_failure_propagates(monkeypatch):
    class _FailLauncher(_SpyLauncher):
        def start(self):
            super().start()
            return 5

    spy = _FailLauncher()
    monkeypatch.setattr(main, "_make_launcher", lambda: spy)
    monkeypatch.setattr(main, "_cdp_health", lambda: False)
    monkeypatch.setattr(main.time, "sleep", lambda _: None)
    with pytest.raises(main.typer.Exit) as exc:
        main._up_impl(restart=False, timeout=5)
    assert exc.value.exit_code == 5
    assert spy.actions == ["start"]


def test_up_timeout_when_never_ready(monkeypatch):
    _patch_launcher(monkeypatch)
    monkeypatch.setattr(main, "_cdp_health", lambda: False)
    monkeypatch.setattr(main.time, "sleep", lambda _: None)
    # monotonic advances past the deadline on the second read
    clock = iter([100.0, 100.0, 200.0])
    monkeypatch.setattr(main.time, "monotonic", lambda: next(clock))
    with pytest.raises(main.typer.Exit) as exc:
        main._up_impl(restart=False, timeout=5)
    assert exc.value.exit_code == 1
