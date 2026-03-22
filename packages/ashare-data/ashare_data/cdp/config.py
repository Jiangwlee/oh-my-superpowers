"""CDP collector configuration."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_SCRIPT_CANDIDATES = (
    Path("/home/bruce/Projects/chrome-cdp-skill/skills/chrome-cdp/scripts/cdp.mjs"),
    Path("/home/bruce/.agents/skills/chrome-cdp/scripts/cdp.mjs"),
    Path("skills/chrome-cdp/scripts/cdp.mjs"),
)


def get_cdp_base_url() -> str:
    """Return the Chrome remote-debugging base URL."""
    return os.getenv("ASHARE_CDP_BASE_URL", "http://127.0.0.1:9222").rstrip("/")


def get_cdp_timeout() -> float:
    """Return the CDP collector timeout in seconds."""
    try:
        return float(os.getenv("ASHARE_CDP_TIMEOUT", "15"))
    except ValueError:
        return 15.0


def get_cdp_script() -> str:
    """Return the cdp helper script path."""
    configured = os.getenv("ASHARE_CDP_SCRIPT")
    if configured:
        return configured
    for candidate in _DEFAULT_SCRIPT_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return str(_DEFAULT_SCRIPT_CANDIDATES[0])
