"""Base declarativa de SQLAlchemy.

No importa modelos aquí para evitar import circular (los modelos importan `Base`).
Para registrar todas las tablas en `Base.metadata` (Alembic / create_all), importa el paquete
`app.models`, que reúne todos los modelos.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
