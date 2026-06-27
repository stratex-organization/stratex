"""Configuración de la conexión a la base de datos (SQLAlchemy)."""

from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL, DEBUG
from models import Base

logger = logging.getLogger(__name__)

# `pool_pre_ping` evita errores por conexiones muertas en el pool.
engine = create_engine(DATABASE_URL, echo=DEBUG, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Crea todas las tablas declaradas si aún no existen."""
    logger.info("Inicializando esquema de base de datos...")
    Base.metadata.create_all(bind=engine)
    logger.info("Esquema listo.")


def get_session() -> Session:
    """Devuelve una nueva sesión de base de datos."""
    return SessionLocal()
