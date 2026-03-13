"""Repository for retained task run records.

Purpose: Persist one retained run row per task execution.
"""

from __future__ import annotations

from app.models.run import Run


def save_run(session, run: Run) -> Run:
    """Persist one run record."""
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
