"""Retention helpers for ephemeral data.

Purpose: Remove expired files from the ephemeral data layer without touching retained DB assets.

Public API:
    cleanup_ephemeral(...) -> int
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


def cleanup_ephemeral(root: Path, *, max_age_days: int) -> int:
    """Remove expired files under the ephemeral root and return removed count."""
    if not root.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified <= cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    return removed
