#!/usr/bin/env python3
"""Evolution history — 查看当前项目的演进历史。

用法：
    history.py [--limit <n>] [--project-root <dir>]
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from scan import EVOLUTION_DATA_DIR


def _detect_project_root() -> Path:
    """检测当前项目根目录。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return Path.cwd()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evolution history")
    parser.add_argument(
        "--limit", type=int, default=20, help="显示最近 N 条记录（默认 20）"
    )
    parser.add_argument("--project-root", type=str, default=None)
    args = parser.parse_args()

    project_root = (
        Path(args.project_root) if args.project_root else _detect_project_root()
    )
    project_name = project_root.name

    results_file = EVOLUTION_DATA_DIR / "projects" / project_name / "results.tsv"

    if not results_file.exists():
        print(f"No evolution history for project: {project_name}")
        print(f"Expected file: {results_file}")
        return

    lines = results_file.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        print("Empty results file.")
        return

    header = lines[0]
    data_lines = lines[1:]

    # 取最后 N 条
    if args.limit and len(data_lines) > args.limit:
        data_lines = data_lines[-args.limit :]

    # 格式化输出
    print(header)
    print("-" * len(header.expandtabs(12)))
    for line in data_lines:
        print(line)

    print(f"\n共 {len(lines) - 1} 条记录（显示最近 {len(data_lines)} 条）")


if __name__ == "__main__":
    main()
