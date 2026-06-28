"""Reúne todos los modelos para registrarlos en Base.metadata (Alembic / create_all)."""

from app.models.user import User  # noqa: F401

__all__ = ["User"]
