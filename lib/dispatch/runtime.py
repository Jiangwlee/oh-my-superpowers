"""Build per-runtime invocation pipelines.

Each runtime is invoked with session-isolation flags so dispatched workers do
not pollute the local project's session history:

    claude  --no-session-persistence
    codex   --ephemeral
    pi      --no-session

Output redirection (`tee`) and exit-code capture are handled by `core.spawn`,
not here — `build_runtime_command` returns just the runtime invocation.
"""

from __future__ import annotations

import shlex

VALID_RUNTIMES = ("claude", "codex", "pi")


def build_runtime_command(
    runtime: str,
    *,
    prompt_file: str,
    model: str | None = None,
) -> str:
    """Return a shell pipeline that invokes the runtime against `prompt_file`.

    The returned string is a fragment that gets composed into a larger script
    by `core.spawn` (which adds `tee` for output capture and `set -o pipefail`
    for exit-code propagation).
    """
    if runtime not in VALID_RUNTIMES:
        raise ValueError(f"unsupported runtime: {runtime!r}")

    pf = shlex.quote(prompt_file)

    if runtime == "claude":
        parts = [
            "cat", pf, "|",
            "claude", "-p",
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]
        if model:
            parts += ["--model", shlex.quote(model)]
    elif runtime == "codex":
        parts = [
            "cat", pf, "|",
            "codex", "exec",
            "--ephemeral",
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        if model:
            parts += ["-m", shlex.quote(model)]
        parts += ["-"]
    elif runtime == "pi":
        # @file token: quote the whole `@PATH` so paths with spaces/metachars survive
        parts = ["pi", "--no-session", "-p", shlex.quote(f"@{prompt_file}")]
        if model:
            parts += ["--model", shlex.quote(model)]
    else:
        raise ValueError(f"unsupported runtime: {runtime!r}")

    return " ".join(parts)
