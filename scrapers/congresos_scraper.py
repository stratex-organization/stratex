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

from ai.extractor import elegir_seccion, filtrar_publicaciones
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


def _fetch(url: str, via_scraper: bool, render_js: bool = False) -> str:
    http = build_session(via_scraper=via_scraper, render_js=render_js)
    resp = http.get(url, timeout=90 if via_scraper else 20)
    resp.raise_for_status()
    return resp.text


def _descargar(url: str, render_js: bool) -> str:
    """Descarga directa y, si falla o trae poco, vía ScrapingBee."""
    try:
        html = _fetch(url, via_scraper=False)
        if len(html) >= 2000 and not render_js:
            return html
    except Exception:  # noqa: BLE001 - caemos al scraper
        pass
    return _fetch(url, via_scraper=True, render_js=render_js)


def run_congreso(
    db: Session,
    clave: str,
    hoy: date | None = None,
    render_js: bool = False,
    profundo: bool = False,
) -> ScrapeResult:
    """Extrae publicaciones de un congreso estatal.

    Args:
        render_js: pide a ScrapingBee renderizar JS (para portales SPA).
        profundo: si la portada no da publicaciones, la IA localiza la sección
            de boletines/noticias y se extrae de esa segunda página.
    """
    hoy = hoy or date.today()
    if clave not in _BY_CLAVE:
        r = ScrapeResult(fuente=clave)
        r.registrar_error(f"Clave de congreso desconocida: {clave}")
        r.fallo = True
        return r

    _, nombre, url = _BY_CLAVE[clave]
    result = ScrapeResult(fuente=nombre)

    # 1) Descarga de la portada.
    try:
        html = _descargar(url, render_js)
    except Exception as exc:  # noqa: BLE001
        result.fallo = True
        result.registrar_error(f"[{nombre}] inaccesible: {exc}")
        return result

    try:
        candidatos = _collect_links(html, url)
        items = filtrar_publicaciones(candidatos, nombre)

        # 2) Crawl de 2º nivel: la portada solo tenía secciones.
        if not items and profundo:
            seccion = elegir_seccion(candidatos, nombre)
            if seccion:
                logger.info("[%s] crawl 2º nivel -> %s", nombre, seccion)
                try:
                    html2 = _descargar(seccion, render_js)
                    cand2 = _collect_links(html2, seccion)
                    items = filtrar_publicaciones(cand2, nombre)
                    result.estrategia = "IA-2niveles"
                except Exception as exc:  # noqa: BLE001
                    result.registrar_error(f"[{nombre}] sección falló: {exc}")

        if not result.estrategia or result.estrategia == "ninguna":
            result.estrategia = "IA"

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
        persistir(db, pubs, result)
        logger.info("[%s] %d publicaciones.", nombre, len(pubs))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        result.fallo = True
        result.registrar_error(f"[{nombre}] error al extraer/persistir: {exc}")

    return result


def run_congresos(
    db: Session,
    claves: list[str],
    hoy: date | None = None,
    render_js: bool = False,
    profundo: bool = False,
) -> list[ScrapeResult]:
    """Ejecuta varios congresos estatales por clave."""
    return [
        run_congreso(db, c, hoy, render_js=render_js, profundo=profundo)
        for c in claves
    ]


def run_todos(db: Session, hoy: date | None = None) -> list[ScrapeResult]:
    """Ejecuta los 32 congresos (vía directa primero; ScrapingBee como respaldo).

    Usa render_js=False para no agotar la cuota: intenta directo y solo recurre
    a ScrapingBee (sin render) cuando el sitio bloquea por IP. `profundo=True`
    activa el crawl de 2º nivel (sección de boletines) cuando la portada no da
    publicaciones.
    """
    claves = [c[0] for c in CONGRESOS]
    return run_congresos(db, claves, hoy=hoy, render_js=False, profundo=True)
