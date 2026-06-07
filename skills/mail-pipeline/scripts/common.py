"""Shared helpers for the mail-pipeline skill."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "mail-pipeline"


def data_dir() -> Path:
    """Return the mail-pipeline data directory."""

    env = os.environ.get("MAIL_PIPELINE_DATA_DIR")
    return Path(env).expanduser() if env else DEFAULT_DATA_DIR
