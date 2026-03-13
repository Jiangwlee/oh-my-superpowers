"""Task entrypoint for ephemeral data cleanup."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.services.retention_service import cleanup_ephemeral


def run(*, max_age_days: int = 3) -> dict[str, Any]:
    """Clean up expired ephemeral files."""
    settings = get_settings()
    removed = cleanup_ephemeral(settings.ephemeral_dir, max_age_days=max_age_days)
    return {
        "ephemeral_dir": str(settings.ephemeral_dir),
        "max_age_days": max_age_days,
        "removed_files": removed,
    }
