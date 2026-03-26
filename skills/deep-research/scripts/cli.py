"""Unified CLI entrypoint for the deep-research skill."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_MAP = {
    "init": "init.py",
    "save-source": "save_source.py",
    "update-state": "update_state.py",
    "build-report": "build_report.py",
}


def main() -> int:
    """Dispatch to the corresponding deep-research subcommand script."""

    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(
            "\n".join(
                [
                    "usage: omp-deep-research <subcommand> [args]",
                    "",
                    "subcommands:",
                    "  init",
                    "  save-source",
                    "  update-state",
                    "  build-report",
                ]
            )
        )
        return 0

    subcommand = args[0]
    script_name = SCRIPT_MAP.get(subcommand)
    if script_name is None:
        print(f"unknown subcommand: {subcommand}", file=sys.stderr)
        return 1

    script_path = Path(__file__).with_name(script_name)
    cmd = [sys.executable, str(script_path), *args[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
