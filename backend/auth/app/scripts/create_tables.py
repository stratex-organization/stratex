"""Crea las tablas directamente en la base de datos (sin Alembic).

Útil para desarrollo/pruebas rápidas. Usa la conexión de `DATABASE_URL` (.env).
Para producción se recomienda Alembic (`alembic upgrade head`).

Uso:
    python -m app.scripts.create_tables
"""

from __future__ import annotations

import asyncio

import app.models  # noqa: F401  -- registra los modelos en Base.metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"[OK] Tablas creadas/verificadas en: {settings.DATABASE_URL}")


if __name__ == "__main__":
    asyncio.run(main())
