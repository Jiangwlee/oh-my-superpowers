"""Task entrypoint for emotion fact build."""

from __future__ import annotations

from typing import Any

from app.core.runtime import today_cn
from app.pipelines.build_emotion_facts import build_emotion_facts
from app.tasks._run_logging import run_logged


def run(*, trade_date: str | None = None) -> dict[str, Any]:
    """Build retained market and theme emotion facts."""
    return run_logged(
        pipeline_name="build-emotion-facts",
        trade_date=trade_date or today_cn(),
        task_fn=build_emotion_facts,
    )
