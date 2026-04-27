"""Build per-runtime shell command strings.

Each runtime is invoked with session-isolation flags so dispatched workers do
not pollute the local project's session history:

    claude  --no-session-persistence
    codex   --ephemeral
    pi      --no-session
"""

from __future__ import annotations

import shlex

VALID_RUNTIMES = ("claude", "codex", "pi")


def build_runtime_command(
    runtime: str,
    *,
    prompt_file: str,
    output_file: str,
    model: str | None = None,
) -> str:
    """Return a shell command string that runs the runtime and tees output.

    The returned string is intended to be passed to `tmux new-session -d <cmd>`
    (which hands it to a shell for parsing).
    """
    if runtime not in VALID_RUNTIMES:
        raise ValueError(f"unsupported runtime: {runtime!r}")

    pf = shlex.quote(prompt_file)
    of = shlex.quote(output_file)

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
        parts = ["pi", "--no-session", "-p", f"@{prompt_file}"]
        if model:
            parts += ["--model", shlex.quote(model)]
    else:
        raise ValueError(f"unsupported runtime: {runtime!r}")

    return f"{' '.join(parts)} 2>&1 | tee {of}"
