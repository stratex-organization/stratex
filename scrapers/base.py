"""Utilidades compartidas por todos los scrapers de fuentes oficiales.

Define la representación intermedia `Publicacion`, el resumen `ScrapeResult`,
la persistencia con deduplicación y helpers comunes (fechas, limpieza de
texto, retrasos corteses). Cada scraper concreto solo produce una lista de
`Publicacion`; la persistencia es uniforme.
"""

from __future__ import annotations

import html
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import SCRAPER_MAX_DELAY, SCRAPER_MIN_DELAY
from models import PublicacionOficial

logger = logging.getLogger(__name__)


@dataclass
class Publicacion:
    """Representación intermedia de una publicación antes de persistirla."""

    fuente: str
    titulo: str
    url_origen: str
    fecha_publicacion: date | None = None
    url_pdf: str | None = None
    tipo_edicion: str | None = None
    texto_limpio: str | None = None


@dataclass
class ScrapeResult:
    """Resumen del resultado de una ejecución de un scraper."""

    fuente: str = ""
    nuevas: int = 0
    duplicadas: int = 0
    estrategia: str = "ninguna"
    fallo: bool = False
    errores: list[str] = field(default_factory=list)

    def registrar_error(self, msg: str) -> None:
        logger.error(msg)
        self.errores.append(msg)


def polite_delay() -> None:
    """Pausa aleatoria entre peticiones para no saturar el servidor."""
    time.sleep(random.uniform(SCRAPER_MIN_DELAY, SCRAPER_MAX_DELAY))


def parse_fecha(valor: str | None) -> date | None:
    """Parsea una fecha desde varios formatos comunes en sitios MX."""
    if not valor:
        return None
    valor = valor.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def limpiar_texto(valor: str | None) -> str | None:
    """Decodifica entidades HTML y elimina etiquetas, dejando texto plano."""
    if not valor:
        return None
    texto = html.unescape(valor)
    texto = BeautifulSoup(texto, "html.parser").get_text(" ", strip=True)
    return texto or None


def persistir(
    db: Session, publicaciones: list[Publicacion], result: ScrapeResult
) -> None:
    """Inserta publicaciones nuevas; ignora las ya existentes por url_origen."""
    for pub in publicaciones:
        existe = db.scalar(
            select(PublicacionOficial.id).where(
                PublicacionOficial.url_origen == pub.url_origen
            )
        )
        if existe:
            result.duplicadas += 1
            continue

        db.add(
            PublicacionOficial(
                fuente=pub.fuente,
                titulo=pub.titulo,
                fecha_publicacion=pub.fecha_publicacion,
                url_origen=pub.url_origen,
                url_pdf=pub.url_pdf,
                tipo_edicion=pub.tipo_edicion,
                texto_limpio=pub.texto_limpio,
                procesado_por_ia=False,
            )
        )
        result.nuevas += 1

    db.commit()
