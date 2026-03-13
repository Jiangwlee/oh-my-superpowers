"""Database session helpers for the backend.

Purpose: Create SQLite engines and session factories based on current runtime settings.

Public API:
    get_engine() -> Engine
    get_session_local() -> sessionmaker
    open_session() -> Session
    reset_db_runtime() -> None
    init_db() -> None
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.base import Base


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Build an engine for the current retained DB path."""
    settings = get_settings()
    return create_engine(f"sqlite:///{settings.database_path}", future=True)


@lru_cache(maxsize=1)
def get_session_local() -> sessionmaker:
    """Build a session factory for the current engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


@contextmanager
def open_session() -> Session:
    """Open a session with automatic close."""
    session = get_session_local()()
    try:
        yield session
    finally:
        session.close()


def reset_db_runtime() -> None:
    """Clear cached engine/session objects after config changes in tests or tasks."""
    get_session_local.cache_clear()
    get_engine.cache_clear()


def init_db() -> None:
    """Create retained tables for local development."""
    Base.metadata.create_all(bind=get_engine())
