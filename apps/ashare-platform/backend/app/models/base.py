"""Shared SQLAlchemy base for backend models.

Purpose: Provide the declarative base for retained daily fact models.

Public API:
    Base -- declarative base class
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for backend models."""

