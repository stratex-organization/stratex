"""Modelos de datos (SQLAlchemy) para StrateX RegTech.

Define la tabla `publicaciones_oficiales`, núcleo del repositorio de
publicaciones regulatorias extraídas de fuentes oficiales mexicanas.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    # Cuerpo completo de la publicación (descargado del detalle, opcional).
    texto_completo: Mapped[str | None] = mapped_column(Text, nullable=True)

    procesado_por_ia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # ---- Resultados del análisis con IA (Claude) ----
    resumen_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    tipo_documento: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nivel_relevancia: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    entidades: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    palabras_clave: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # ---- Inteligencia enfocada a Xignux (módulo de Regulación) ----
    # Autoridad que emite el documento (p. ej. CRE, COFEPRIS, SAT).
    autoridad_emisora: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Empresas / productos / plantas de Xignux potencialmente afectados.
    empresas_afectadas: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    productos_afectados: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    plantas_afectadas: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    # Crítico | Alto | Medio | Bajo | Solo monitoreo
    nivel_riesgo: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    # Inmediato | Corto plazo | Mediano plazo | Largo plazo | Indeterminado
    horizonte_impacto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # ¿Por qué le importa a Xignux?
    por_que_importa: Mapped[str | None] = mapped_column(Text, nullable=True)
    impacto_potencial: Mapped[str | None] = mapped_column(Text, nullable=True)
    accion_recomendada: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_responsable: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Payload completo del análisis (para trazabilidad / campos futuros).
    analisis_ia: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    procesado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # True cuando ya se emitió una alerta por esta publicación.
    alertado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Marcas de gestión desde el frontend.
    revisado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    descartado: Mapped[bool] = mapped_column(
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


# ---------------------------------------------------------------------------
# Núcleo de conocimiento de Xignux (administrable desde la base de datos)
# ---------------------------------------------------------------------------
# Estas tablas describen QUIÉN es Xignux: sus empresas, productos, plantas,
# marcas y temas estratégicos, además del catálogo de autoridades regulatorias.
# La capa de IA las lee (vía ai/knowledge.py) para enfocar el análisis en el
# impacto real para el grupo, en lugar de un análisis regulatorio genérico.


class EmpresaXignux(Base):
    """Una empresa del grupo Xignux dentro del alcance del sistema."""

    __tablename__ = "empresas_xignux"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    # "Energía", "Alimentos", "Botanas", etc.
    unidad_negocio: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # False para empresas excluidas explícitamente (p. ej. Prolec GE).
    en_alcance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EmpresaXignux {self.nombre!r} ({self.unidad_negocio})>"


class ProductoXignux(Base):
    """Producto relevante asociado a una empresa de Xignux."""

    __tablename__ = "productos_xignux"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas_xignux.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)


class MarcaXignux(Base):
    """Marca comercial asociada a una empresa de Xignux."""

    __tablename__ = "marcas_xignux"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas_xignux.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)


class UbicacionXignux(Base):
    """Planta o ubicación relevante de una empresa de Xignux."""

    __tablename__ = "ubicaciones_xignux"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas_xignux.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nombre de la planta (p. ej. "Planta Kalos"); puede ser None si es genérica.
    nombre: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(120), nullable=True)


class TemaEstrategico(Base):
    """Tema estratégico que Xignux vigila (global o por empresa)."""

    __tablename__ = "temas_estrategicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nullable: un tema puede ser transversal a todo el grupo.
    empresa_id: Mapped[int | None] = mapped_column(
        ForeignKey("empresas_xignux.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)


class AutoridadRegulatoria(Base):
    """Autoridad u órgano relevante para el monitoreo de Xignux."""

    __tablename__ = "autoridades_regulatorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    siglas: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # "Energía", "Salud y Alimentos", "Medio Ambiente", "Economía y Comercio
    # Exterior", "Laboral", "Legislativo", "Judicial".
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AutoridadRegulatoria {self.siglas or self.nombre!r}>"
