"""Descarga del cuerpo completo de las publicaciones.

Hoy `texto_limpio` guarda solo el resumen del sumario. Este módulo descarga la
nota completa (para el DOF, el contenedor `#DivDetalleNota` de `nota_detalle.php`)
y la almacena en `texto_completo`, mejorando la calidad del análisis por IA.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from scrapers.base import polite_delay
from scrapers.http_client import build_session
from models import PublicacionOficial

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 25
# Límite defensivo de caracteres a almacenar por nota.
MAX_CHARS = 60_000
# Fuentes con extracción de cuerpo confiable (selector dedicado).
FULL_TEXT_SOURCES = {"DOF"}


def _extraer_cuerpo_dof(html_bytes: bytes) -> str | None:
    """Extrae el cuerpo del decreto desde una página nota_detalle del DOF."""
    from bs4 import BeautifulSoup

    # El DOF sirve la página en ISO-8859-1.
    soup = BeautifulSoup(html_bytes.decode("latin-1", "ignore"), "html.parser")
    cont = soup.select_one("#DivDetalleNota")
    if not cont:
        return None
    texto = cont.get_text("\n", strip=True)
    return texto[:MAX_CHARS] if texto else None


def fetch_full_text(session, pub: PublicacionOficial) -> str | None:
    """Descarga y extrae el cuerpo completo de una publicación (si es posible)."""
    resp = session.get(pub.url_origen, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    if pub.fuente == "DOF":
        return _extraer_cuerpo_dof(resp.content)

    # Fuentes genéricas: tomamos el texto visible del documento como respaldo.
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    texto = soup.get_text("\n", strip=True)
    return texto[:MAX_CHARS] if texto else None


def descargar_pendientes(db: Session, limite: int | None = None) -> int:
    """Descarga el texto completo de las publicaciones que aún no lo tienen.

    Returns:
        Número de publicaciones a las que se les agregó texto completo.
    """
    consulta = (
        select(PublicacionOficial)
        .where(PublicacionOficial.texto_completo.is_(None))
        .where(PublicacionOficial.fuente.in_(FULL_TEXT_SOURCES))
        .order_by(PublicacionOficial.creado_en)
    )
    if limite and limite > 0:
        consulta = consulta.limit(limite)

    pendientes = list(db.scalars(consulta))
    if not pendientes:
        return 0

    logger.info("Descargando texto completo de %d publicaciones...", len(pendientes))
    http = build_session()
    actualizadas = 0

    for pub in pendientes:
        try:
            cuerpo = fetch_full_text(http, pub)
            if cuerpo:
                pub.texto_completo = cuerpo
                db.commit()
                actualizadas += 1
            else:
                db.rollback()
            polite_delay()
        except Exception as exc:  # noqa: BLE001 - aislamos el fallo por registro
            db.rollback()
            logger.warning("No se pudo descargar %s: %s", pub.url_origen, exc)

    logger.info("Texto completo agregado a %d publicaciones.", actualizadas)
    return actualizadas
