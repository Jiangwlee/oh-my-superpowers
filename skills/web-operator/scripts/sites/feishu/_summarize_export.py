#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["openpyxl"]
# ///
"""Summarize a Feishu approval export directory.

Reads the first cell (Filter row) of every .xlsx in the given directory
and extracts the per-file `Total: N request(s)` count. Outputs a JSON
object to stdout: {files: [...], types: N, total_requests: N}.
"""

import json
import re
import sys
from pathlib import Path

import openpyxl

TOTAL_RE = re.compile(r"Total:\s*(\d+)\s*request\(s\)", re.IGNORECASE)


def summarize(export_dir: Path) -> dict:
    files: list[dict] = []
    grand_total = 0
    for path in sorted(export_dir.glob("*.xlsx")):
        try:
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            ws = wb.active
            header = ws.cell(1, 1).value or ""
            wb.close()
        except Exception as exc:
            files.append({"name": path.name, "error": str(exc)})
            continue

        match = TOTAL_RE.search(str(header))
        count = int(match.group(1)) if match else None
        if count is not None:
            grand_total += count
        files.append({"name": path.name, "total_requests": count})
    return {
        "files": [f["name"] for f in files],
        "types": len(files),
        "total_requests": grand_total,
        "per_file": files,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: _summarize_export.py <extract_dir>", file=sys.stderr)
        return 2
    export_dir = Path(sys.argv[1])
    if not export_dir.is_dir():
        print(f"not a directory: {export_dir}", file=sys.stderr)
        return 1
    print(json.dumps(summarize(export_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
