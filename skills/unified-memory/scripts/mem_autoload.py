#!/usr/bin/env python3
"""Wrapper for /mem-autoload slash command.

Loads only top topics (no content) from project memory.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    script_dir = Path(__file__).resolve().parent
    memory_cli = script_dir / "memory_cli.py"
    project_dir = Path.cwd()

    # Delegate to the main CLI so behavior stays centralized.
    import subprocess

    cmd = [
        sys.executable,
        str(memory_cli),
        "--project-dir",
        str(project_dir),
        "autoload-topics",
        "--limit",
        "20",
        *argv,
    ]
    result = subprocess.run(cmd, text=True)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
