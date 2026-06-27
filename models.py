"""Modelos de datos (SQLAlchemy) para StrateX RegTech.

Define la tabla `publicaciones_oficiales`, núcleo del repositorio de
publicaciones regulatorias extraídas de fuentes oficiales mexicanas.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""


class PublicacionOficial(Base):
    """Una publicación oficial (decreto, acuerdo, iniciativa, etc.)."""

    __tablename__ = "publicaciones_oficiales"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    fuente: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_publicacion: Mapped[date | None] = mapped_column(
        Date, nullable=True, index=True
    )

    # url_origen es única: sirve como llave natural para deduplicación.
    url_origen: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    url_pdf: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "Matutina", "Vespertina", "Extraordinaria" (específico del DOF).
    tipo_edicion: Mapped[str | None] = mapped_column(String(40), nullable=True)

    texto_limpio: Mapped[str | None] = mapped_column(Text, nullable=True)

    procesado_por_ia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover - utilidad de depuración
        return (
            f"<PublicacionOficial fuente={self.fuente!r} "
            f"fecha={self.fecha_publicacion} titulo={self.titulo[:40]!r}>"
        )
