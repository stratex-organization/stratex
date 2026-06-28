"""Bot extractor del Diario Oficial de la Federación (DOF).

Estrategia híbrida:
  - Estrategia A (preferida): feed RSS "Sumario" del DOF
    (https://www.dof.gob.mx/sumario.xml) vía `feedparser`.
  - Estrategia B (fallback): scraping HTML del índice con `BeautifulSoup`.

Particularidades del feed real del DOF:
  - No trae `pubDate`; la fecha va en el enlace como `...&fecha=DD/MM/AAAA`.
  - `<title>` = dependencia/sección emisora; `<description>` = título del acto.
  - El "Sumario" es la edición vigente del día.

Reutiliza `scrapers.base` para la representación, persistencia y helpers.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from urllib.parse import parse_qs, urljoin, urlparse

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from config import DOF_INDEX_URL, DOF_RSS_URL
from scrapers.base import (
    Publicacion,
    ScrapeResult,
    limpiar_texto,
    parse_fecha,
    persistir,
    polite_delay,
)
from scrapers.http_client import build_session

logger = logging.getLogger(__name__)

FUENTE = "DOF"
REQUEST_TIMEOUT = 25  # segundos


def _fecha_desde_link(url: str) -> date | None:
    """Extrae la fecha del parámetro `fecha=DD/MM/AAAA` del enlace."""
    try:
        qs = parse_qs(urlparse(url).query)
    except ValueError:
        return None
    valores = qs.get("fecha")
    return parse_fecha(valores[0]) if valores else None


def _inferir_tipo_edicion(texto: str | None, default: str | None = None) -> str | None:
    """Deduce el tipo de edición (Matutina/Vespertina/Extraordinaria)."""
    if texto:
        t = texto.lower()
        if "extraordinar" in t:
            return "Extraordinaria"
        if "vespertin" in t:
            return "Vespertina"
        if "matutin" in t:
            return "Matutina"
    return default


def _extraer_via_rss(session, hoy: date) -> list[Publicacion]:
    """Consume el feed RSS "Sumario" y devuelve las notas de la edición vigente."""
    logger.info("Estrategia A (RSS): consultando %s", DOF_RSS_URL)

    resp = session.get(DOF_RSS_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Feed RSS inválido o vacío: {feed.get('bozo_exception')}")
    if not feed.entries:
        return []

    crudas: list[tuple[str, str, date | None, str | None]] = []
    for entry in feed.entries:
        url_origen = entry.get("link")
        seccion = (entry.get("title") or "").strip()
        descripcion = limpiar_texto(entry.get("summary") or entry.get("description"))
        if not url_origen:
            continue
        fecha_pub = _fecha_desde_link(url_origen) or parse_fecha(entry.get("published"))
        crudas.append((url_origen, seccion, fecha_pub, descripcion))

    if not crudas:
        return []

    fechas = [f for *_x, f, _d in crudas if f is not None]
    edicion = max(fechas) if fechas else hoy
    logger.info("RSS: edición vigente detectada con fecha %s", edicion)

    publicaciones: list[Publicacion] = []
    for url_origen, seccion, fecha_pub, descripcion in crudas:
        if fecha_pub and fecha_pub != edicion:
            continue
        titulo = descripcion or seccion or "(sin título)"
        contexto = " — ".join(p for p in (seccion, descripcion) if p) or None
        tipo = _inferir_tipo_edicion(
            f"{seccion} {descripcion or ''}", default="Matutina"
        )
        publicaciones.append(
            Publicacion(
                fuente=FUENTE,
                titulo=titulo,
                url_origen=url_origen,
                fecha_publicacion=fecha_pub or edicion,
                url_pdf=None,
                tipo_edicion=tipo,
                texto_limpio=contexto,
            )
        )

    logger.info("RSS: %d publicaciones de la edición vigente.", len(publicaciones))
    return publicaciones


def _extraer_via_html(session, hoy: date) -> list[Publicacion]:
    """Fallback: navega el índice HTML del DOF y extrae los acuerdos."""
    logger.info("Estrategia B (HTML): navegando %s", DOF_INDEX_URL)

    resp = session.get(DOF_INDEX_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    polite_delay()

    soup = BeautifulSoup(resp.text, "html.parser")
    publicaciones: list[Publicacion] = []
    vistos: set[str] = set()
    patron = re.compile(r"nota_detalle\.php", re.IGNORECASE)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not patron.search(href):
            continue
        titulo = limpiar_texto(a.get_text(" ", strip=True))
        if not titulo:
            continue
        url_origen = urljoin(DOF_INDEX_URL, href)
        if url_origen in vistos:
            continue
        vistos.add(url_origen)
        publicaciones.append(
            Publicacion(
                fuente=FUENTE,
                titulo=titulo,
                url_origen=url_origen,
                fecha_publicacion=_fecha_desde_link(url_origen) or hoy,
                tipo_edicion=_inferir_tipo_edicion(titulo),
                texto_limpio=titulo,
            )
        )

    logger.info("HTML: %d publicaciones candidatas encontradas.", len(publicaciones))
    return publicaciones


def run(db: Session, hoy: date | None = None) -> ScrapeResult:
    """Ejecuta el bot del DOF con estrategia híbrida RSS -> HTML."""
    hoy = hoy or date.today()
    result = ScrapeResult(fuente=FUENTE)
    http = build_session()

    publicaciones: list[Publicacion] = []

    try:
        publicaciones = _extraer_via_rss(http, hoy)
        if publicaciones:
            result.estrategia = "RSS"
    except Exception as exc:  # noqa: BLE001 - capturamos para activar fallback
        result.registrar_error(f"[DOF] Estrategia RSS falló: {exc}")

    if not publicaciones:
        try:
            publicaciones = _extraer_via_html(http, hoy)
            if publicaciones:
                result.estrategia = "HTML"
        except Exception as exc:  # noqa: BLE001
            result.registrar_error(f"[DOF] Estrategia HTML (fallback) falló: {exc}")

    if not publicaciones and result.errores:
        result.fallo = True
        return result

    try:
        persistir(db, publicaciones, result)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        result.fallo = True
        result.registrar_error(f"[DOF] Error al persistir: {exc}")

    return result
