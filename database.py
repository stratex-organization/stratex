"""Configuración de la conexión a la base de datos (SQLAlchemy)."""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL, DEBUG
from models import Base

logger = logging.getLogger(__name__)

# `pool_pre_ping` evita errores por conexiones muertas en el pool.
engine = create_engine(DATABASE_URL, echo=DEBUG, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Columnas de análisis IA: se añaden a tablas ya existentes de forma idempotente.
# (create_all crea tablas faltantes, pero no agrega columnas nuevas.)
_AI_COLUMNS = {
    "resumen_ia": "TEXT",
    "sector": "VARCHAR(80)",
    "tipo_documento": "VARCHAR(80)",
    "nivel_relevancia": "VARCHAR(20)",
    "entidades": "JSONB",
    "palabras_clave": "JSONB",
    "analisis_ia": "JSONB",
    "procesado_en": "TIMESTAMP WITH TIME ZONE",
}


def init_db() -> None:
    """Crea las tablas faltantes y aplica migraciones aditivas idempotentes."""
    logger.info("Inicializando esquema de base de datos...")
    Base.metadata.create_all(bind=engine)
    _ensure_ai_columns()
    logger.info("Esquema listo.")


def _ensure_ai_columns() -> None:
    """Agrega las columnas de análisis IA si aún no existen (PostgreSQL)."""
    with engine.begin() as conn:
        for nombre, tipo in _AI_COLUMNS.items():
            conn.execute(
                text(
                    "ALTER TABLE publicaciones_oficiales "
                    f"ADD COLUMN IF NOT EXISTS {nombre} {tipo}"
                )
            )


def get_session() -> Session:
    """Devuelve una nueva sesión de base de datos."""
    return SessionLocal()
