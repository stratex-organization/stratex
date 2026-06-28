"""Scraper genérico RSS -> HTML para fuentes oficiales adicionales.

Sirve a fuentes cuyo contenido se puede mapear a la tabla `publicaciones_oficiales`
sin lógica de parsing dedicada (CNBV, SAT, Banxico, Cámara de Diputados, etc.).
Cada fuente se describe con un `FuenteConfig`; este módulo aplica la misma
estrategia híbrida y deduplicación que el bot del DOF.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlparse

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

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

REQUEST_TIMEOUT = 25
REQUEST_TIMEOUT_SCRAPER = 95  # ScrapingBee con render_js puede tardar más.


@dataclass
class FuenteConfig:
    """Configuración de una fuente genérica."""

    nombre: str
    rss_url: str | None = None
    index_url: str | None = None
    via_scraper: bool = False   # enrutar por ScrapingBee (sitios bloqueados)
    render_js: bool = False     # renderizar JS (gob.mx y SPAs)


def _extraer_via_rss(session, cfg: FuenteConfig, timeout: int) -> list[Publicacion]:
    logger.info("[%s] Estrategia A (RSS): %s", cfg.nombre, cfg.rss_url)
    resp = session.get(cfg.rss_url, timeout=timeout)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Feed RSS inválido o vacío: {feed.get('bozo_exception')}")

    publicaciones: list[Publicacion] = []
    for entry in feed.entries:
        url_origen = entry.get("link")
        titulo = limpiar_texto(entry.get("title"))
        if not url_origen or not titulo:
            continue

        fecha_pub: date | None = None
        if entry.get("published_parsed"):
            t = entry.published_parsed
            fecha_pub = date(t.tm_year, t.tm_mon, t.tm_mday)
        else:
            fecha_pub = parse_fecha(entry.get("published"))

        resumen = limpiar_texto(entry.get("summary") or entry.get("description"))
        url_pdf = next(
            (
                link.get("href")
                for link in entry.get("links", [])
                if link.get("href", "").lower().endswith(".pdf")
            ),
            None,
        )

        publicaciones.append(
            Publicacion(
                fuente=cfg.nombre,
                titulo=titulo,
                url_origen=url_origen,
                fecha_publicacion=fecha_pub,
                url_pdf=url_pdf,
                texto_limpio=resumen or titulo,
            )
        )

    logger.info("[%s] RSS: %d publicaciones.", cfg.nombre, len(publicaciones))
    return publicaciones


def _extraer_via_html(
    session, cfg: FuenteConfig, hoy: date, timeout: int
) -> list[Publicacion]:
    logger.info("[%s] Estrategia B (HTML): %s", cfg.nombre, cfg.index_url)
    resp = session.get(cfg.index_url, timeout=timeout)
    resp.raise_for_status()
    polite_delay()

    soup = BeautifulSoup(resp.text, "html.parser")
    base_host = urlparse(cfg.index_url).netloc
    publicaciones: list[Publicacion] = []
    vistos: set[str] = set()

    # Heurística: enlaces internos con texto sustancial (títulos de notas).
    for a in soup.find_all("a", href=True):
        titulo = limpiar_texto(a.get_text(" ", strip=True))
        if not titulo or len(titulo) < 30:
            continue
        url_origen = urljoin(cfg.index_url, a["href"])
        if urlparse(url_origen).netloc != base_host:
            continue
        if url_origen in vistos:
            continue
        vistos.add(url_origen)
        publicaciones.append(
            Publicacion(
                fuente=cfg.nombre,
                titulo=titulo,
                url_origen=url_origen,
                fecha_publicacion=hoy,
                texto_limpio=titulo,
            )
        )

    logger.info("[%s] HTML: %d candidatas.", cfg.nombre, len(publicaciones))
    return publicaciones


def run(db: Session, cfg: FuenteConfig, hoy: date | None = None) -> ScrapeResult:
    """Ejecuta una fuente genérica con estrategia híbrida RSS -> HTML."""
    hoy = hoy or date.today()
    result = ScrapeResult(fuente=cfg.nombre)
    http = build_session(via_scraper=cfg.via_scraper, render_js=cfg.render_js)
    # Con ScrapingBee + render el tiempo de respuesta es mayor.
    timeout = REQUEST_TIMEOUT_SCRAPER if cfg.via_scraper else REQUEST_TIMEOUT
    publicaciones: list[Publicacion] = []

    if cfg.rss_url:
        try:
            publicaciones = _extraer_via_rss(http, cfg, timeout)
            if publicaciones:
                result.estrategia = "RSS"
        except Exception as exc:  # noqa: BLE001
            result.registrar_error(f"[{cfg.nombre}] RSS falló: {exc}")

    if not publicaciones and cfg.index_url:
        try:
            publicaciones = _extraer_via_html(http, cfg, hoy, timeout)
            if publicaciones:
                result.estrategia = "HTML"
        except Exception as exc:  # noqa: BLE001
            result.registrar_error(f"[{cfg.nombre}] HTML falló: {exc}")

    if not publicaciones:
        if result.errores:
            result.fallo = True
        return result

    try:
        persistir(db, publicaciones, result)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        result.fallo = True
        result.registrar_error(f"[{cfg.nombre}] Error al persistir: {exc}")

    return result
