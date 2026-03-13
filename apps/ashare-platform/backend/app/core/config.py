"""Backend runtime configuration.

Purpose: Resolve filesystem locations for ephemeral files and retained data.

Public API:
    Settings -- immutable runtime settings container
    settings -- lazily constructed runtime settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Resolved backend settings."""

    home_dir: Path
    data_dir: Path
    ephemeral_dir: Path
    retained_dir: Path
    database_path: Path


def _default_home_dir() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build backend settings and ensure required directories exist."""
    home_dir = Path(os.environ.get("ASHARE_PLATFORM_HOME") or _default_home_dir())
    home_dir.mkdir(parents=True, exist_ok=True)

    data_dir = home_dir / "data"
    ephemeral_dir = data_dir / "ephemeral"
    retained_dir = data_dir / "retained"
    for path in (data_dir, ephemeral_dir, retained_dir):
        path.mkdir(parents=True, exist_ok=True)

    database_path = retained_dir / "ashare_platform.db"
    return Settings(
        home_dir=home_dir,
        data_dir=data_dir,
        ephemeral_dir=ephemeral_dir,
        retained_dir=retained_dir,
        database_path=database_path,
    )


settings = get_settings()
