"""Scraper de congresos estatales con extracción asistida por IA.

Los 32 congresos tienen estructuras HTML distintas. En vez de un parser por
sitio, este runner: (1) descarga la página (directo, o vía ScrapingBee si la
IP extranjera está bloqueada), (2) recolecta los enlaces internos, y (3) deja
que el modelo (DeepSeek) filtre cuáles son publicaciones legislativas reales.
"""

from __future__ import annotations

import logging
from datetime import date
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ai.extractor import filtrar_publicaciones
from scrapers.base import Publicacion, ScrapeResult, persistir
from scrapers.congresos import CONGRESOS
from scrapers.http_client import build_session

logger = logging.getLogger(__name__)

_BY_CLAVE = {c[0]: c for c in CONGRESOS}
# Nombres de las fuentes (para conteos agregados de la rama).
NOMBRES_CONGRESOS = {c[1] for c in CONGRESOS}


def _collect_links(html: str, base: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base).netloc
    cands: list[dict] = []
    vistos: set[str] = set()
    for a in soup.find_all("a", href=True):
        t = a.get_text(" ", strip=True)
        u = urljoin(base, a["href"])
        if len(t) < 8 or u in vistos or urlparse(u).netloc != host:
            continue
        vistos.add(u)
        cands.append({"t": t, "u": u})
    return cands


def _fetch(url: str, via_scraper: bool) -> str:
    http = build_session(via_scraper=via_scraper, render_js=False)
    resp = http.get(url, timeout=90 if via_scraper else 20)
    resp.raise_for_status()
    return resp.text


def run_congreso(db: Session, clave: str, hoy: date | None = None) -> ScrapeResult:
    """Extrae publicaciones de un congreso estatal (directo o vía ScrapingBee)."""
    hoy = hoy or date.today()
    if clave not in _BY_CLAVE:
        r = ScrapeResult(fuente=clave)
        r.registrar_error(f"Clave de congreso desconocida: {clave}")
        r.fallo = True
        return r

    _, nombre, url = _BY_CLAVE[clave]
    result = ScrapeResult(fuente=nombre)

    # 1) Descarga: directo y, si falla o trae poco, vía ScrapingBee.
    html: str | None = None
    try:
        html = _fetch(url, via_scraper=False)
        if len(html) < 2000:
            raise ValueError("contenido insuficiente")
    except Exception as exc:  # noqa: BLE001
        logger.info("[%s] directo falló (%s); reintentando vía ScrapingBee.", nombre, exc)
        try:
            html = _fetch(url, via_scraper=True)
        except Exception as exc2:  # noqa: BLE001
            result.fallo = True
            result.registrar_error(f"[{nombre}] inaccesible: {exc2}")
            return result

    # 2) Enlaces -> 3) filtro IA -> persistencia.
    try:
        candidatos = _collect_links(html, url)
        items = filtrar_publicaciones(candidatos, nombre)
        pubs = [
            Publicacion(
                fuente=nombre,
                titulo=it["titulo"],
                url_origen=it["url"],
                fecha_publicacion=hoy,
                texto_limpio=it["titulo"],
            )
            for it in items
        ]
        result.estrategia = "IA"
        persistir(db, pubs, result)
        logger.info("[%s] %d candidatos -> %d publicaciones.", nombre, len(candidatos), len(pubs))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        result.fallo = True
        result.registrar_error(f"[{nombre}] error al extraer/persistir: {exc}")

    return result


def run_congresos(
    db: Session, claves: list[str], hoy: date | None = None
) -> list[ScrapeResult]:
    """Ejecuta varios congresos estatales por clave."""
    return [run_congreso(db, c, hoy) for c in claves]
