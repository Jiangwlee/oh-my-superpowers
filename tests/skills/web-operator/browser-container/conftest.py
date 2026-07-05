"""Make the container app importable and skip cleanly without its deps.

The app package lives under ``docker/browser-container/`` (installed into the
container's own venv). Put that dir on ``sys.path`` so ``import app...`` resolves
from the repo root, and skip the whole suite when the container's third-party
deps (fastapi / websockets) are not installed in the current interpreter — e.g.
a plain ``omp test`` run outside the container venv.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[4] / "docker" / "browser-container"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

collect_ignore_glob: list[str] = []
if importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("websockets") is None:
    # Deps absent: don't error on import, just skip the runnable tests.
    collect_ignore_glob = ["test_*.py"]
