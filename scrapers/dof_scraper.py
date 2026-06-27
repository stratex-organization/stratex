"""Bot extractor del Diario Oficial de la Federación (DOF).

Implementa una estrategia híbrida:
  - Estrategia A (preferida): consumo del feed RSS "Sumario" del DOF
    (https://www.dof.gob.mx/sumario.xml) vía `feedparser`.
  - Estrategia B (fallback): scraping HTML del índice con `requests` +
    `BeautifulSoup` cuando el RSS falla o no devuelve resultados.

Particularidades del feed real del DOF que maneja este bot:
  - El feed no trae `pubDate`; la fecha de publicación va embebida en el
    enlace de cada nota como `...&fecha=DD/MM/AAAA`.
  - El elemento `<title>` del item contiene la dependencia/sección emisora,
    mientras que `<description>` contiene el título real del acto (decreto,
    acuerdo, etc.), a menudo con entidades HTML (`&oacute;`, etc.).
  - El "Sumario" corresponde por definición a la edición vigente del día; se
    toman todas las notas de la edición más reciente presente en el feed.

Las publicaciones se insertan en la base de datos siempre que su `url_origen`
no exista previamente (deduplicación por llave natural).
"""

from __future__ import annotations

import html
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import parse_qs, urljoin, urlparse

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import (
    DOF_INDEX_URL,
    DOF_RSS_URL,
    SCRAPER_MAX_DELAY,
    SCRAPER_MIN_DELAY,
)
from models import PublicacionOficial
from scrapers.http_client import build_session

logger = logging.getLogger(__name__)

FUENTE = "DOF"
REQUEST_TIMEOUT = 25  # segundos


# --------------------------------------------------------------------------- #
#  Estructuras auxiliares
# --------------------------------------------------------------------------- #
@dataclass
class Publicacion:
    """Representación intermedia de una nota antes de persistirla."""

    titulo: str
    url_origen: str
    fecha_publicacion: date | None = None
    url_pdf: str | None = None
    tipo_edicion: str | None = None
    texto_limpio: str | None = None


@dataclass
class ScrapeResult:
    """Resumen del resultado de una ejecución del scraper."""

    nuevas: int = 0
    duplicadas: int = 0
    estrategia: str = "ninguna"
    fallo: bool = False
    errores: list[str] = field(default_factory=list)

    def registrar_error(self, msg: str) -> None:
        logger.error(msg)
        self.errores.append(msg)


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #
def _polite_delay() -> None:
    """Pausa aleatoria entre peticiones para no saturar el servidor."""
    time.sleep(random.uniform(SCRAPER_MIN_DELAY, SCRAPER_MAX_DELAY))


def _parse_fecha(valor: str | None) -> date | None:
    """Parsea una fecha desde varios formatos comunes del DOF."""
    if not valor:
        return None
    valor = valor.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def _fecha_desde_link(url: str) -> date | None:
    """Extrae la fecha de publicación del parámetro `fecha=DD/MM/AAAA`."""
    try:
        qs = parse_qs(urlparse(url).query)
    except ValueError:
        return None
    valores = qs.get("fecha")
    return _parse_fecha(valores[0]) if valores else None


def _limpiar_texto(valor: str | None) -> str | None:
    """Decodifica entidades HTML y elimina etiquetas, dejando texto plano."""
    if not valor:
        return None
    # Doble paso: feedparser a veces deja entidades sin decodificar.
    texto = html.unescape(valor)
    texto = BeautifulSoup(texto, "html.parser").get_text(" ", strip=True)
    return texto or None


def _inferir_tipo_edicion(
    texto: str | None, default: str | None = None
) -> str | None:
    """Deduce el tipo de edición (Matutina/Vespertina/Extraordinaria).

    Si el texto no contiene una pista explícita, devuelve `default`.
    """
    if texto:
        t = texto.lower()
        if "extraordinar" in t:
            return "Extraordinaria"
        if "vespertin" in t:
            return "Vespertina"
        if "matutin" in t:
            return "Matutina"
    return default


# --------------------------------------------------------------------------- #
#  Estrategia A: RSS (Sumario del DOF)
# --------------------------------------------------------------------------- #
def _extraer_via_rss(session, hoy: date) -> list[Publicacion]:
    """Consume el feed RSS "Sumario" del DOF y devuelve las notas vigentes.

    El Sumario corresponde a la edición publicada más reciente. Se toman todas
    las notas cuya fecha (extraída del enlace) coincida con la edición vigente
    del feed, de modo que la ejecución diaria capture la publicación del día
    sin verse afectada por zonas horarias o retrasos de publicación.
    """
    logger.info("Estrategia A (RSS): consultando %s", DOF_RSS_URL)

    resp = session.get(DOF_RSS_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Feed RSS inválido o vacío: {feed.get('bozo_exception')}")
    if not feed.entries:
        return []

    # Pre-parseo: extraemos campos básicos de cada entry.
    crudas: list[tuple[str, str, date | None, str | None]] = []
    for entry in feed.entries:
        url_origen = entry.get("link")
        seccion = (entry.get("title") or "").strip()  # dependencia emisora
        descripcion = _limpiar_texto(entry.get("summary") or entry.get("description"))
        if not url_origen:
            continue
        fecha_pub = _fecha_desde_link(url_origen) or _parse_fecha(
            entry.get("published")
        )
        crudas.append((url_origen, seccion, fecha_pub, descripcion))

    if not crudas:
        return []

    # Fecha de la edición vigente = la fecha más reciente presente en el feed.
    fechas = [f for *_x, f, _d in crudas if f is not None]
    edicion = max(fechas) if fechas else hoy
    logger.info("RSS: edición vigente detectada con fecha %s", edicion)

    publicaciones: list[Publicacion] = []
    for url_origen, seccion, fecha_pub, descripcion in crudas:
        # Solo notas de la edición vigente (descarta arrastres de otros días).
        if fecha_pub and fecha_pub != edicion:
            continue

        # El título real del acto está en la descripción; la sección sirve de
        # contexto. Si no hay descripción, usamos la sección como título.
        titulo = descripcion or seccion or "(sin título)"
        contexto = " — ".join(p for p in (seccion, descripcion) if p) or None

        # El sumario.xml sin parámetros es la edición ordinaria (Matutina);
        # las extraordinarias/vespertinas se sirven en URLs distintas.
        tipo = _inferir_tipo_edicion(
            f"{seccion} {descripcion or ''}", default="Matutina"
        )

        publicaciones.append(
            Publicacion(
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


# --------------------------------------------------------------------------- #
#  Estrategia B: Fallback HTML
# --------------------------------------------------------------------------- #
def _extraer_via_html(session, hoy: date) -> list[Publicacion]:
    """Fallback: navega el índice HTML del DOF y extrae los acuerdos."""
    logger.info("Estrategia B (HTML): navegando %s", DOF_INDEX_URL)

    resp = session.get(DOF_INDEX_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    _polite_delay()

    soup = BeautifulSoup(resp.text, "html.parser")
    publicaciones: list[Publicacion] = []
    vistos: set[str] = set()

    # El índice del DOF enlaza las notas con nota_detalle.php?codigo=...&fecha=
    patron = re.compile(r"nota_detalle\.php", re.IGNORECASE)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not patron.search(href):
            continue

        titulo = _limpiar_texto(a.get_text(" ", strip=True))
        if not titulo:
            continue

        url_origen = urljoin(DOF_INDEX_URL, href)
        if url_origen in vistos:
            continue
        vistos.add(url_origen)

        fecha_pub = _fecha_desde_link(url_origen) or hoy
        tipo = _inferir_tipo_edicion(titulo)
        publicaciones.append(
            Publicacion(
                titulo=titulo,
                url_origen=url_origen,
                fecha_publicacion=fecha_pub,
                tipo_edicion=tipo,
                texto_limpio=titulo,
            )
        )

    logger.info("HTML: %d publicaciones candidatas encontradas.", len(publicaciones))
    return publicaciones


# --------------------------------------------------------------------------- #
#  Persistencia
# --------------------------------------------------------------------------- #
def _persistir(
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
                fuente=FUENTE,
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


# --------------------------------------------------------------------------- #
#  Punto de entrada del bot
# --------------------------------------------------------------------------- #
def run(db: Session, hoy: date | None = None) -> ScrapeResult:
    """Ejecuta el bot del DOF con estrategia híbrida RSS -> HTML.

    Args:
        db: sesión activa de SQLAlchemy.
        hoy: fecha de referencia (por defecto, la fecha actual del sistema).

    Returns:
        ScrapeResult con el resumen de la corrida.
    """
    hoy = hoy or date.today()
    result = ScrapeResult()
    http = build_session()

    publicaciones: list[Publicacion] = []

    # --- Estrategia A: RSS ---
    try:
        publicaciones = _extraer_via_rss(http, hoy)
        if publicaciones:
            result.estrategia = "RSS"
    except Exception as exc:  # noqa: BLE001 - capturamos para activar fallback
        result.registrar_error(f"Estrategia RSS falló: {exc}")

    # --- Estrategia B: Fallback HTML ---
    if not publicaciones:
        try:
            publicaciones = _extraer_via_html(http, hoy)
            if publicaciones:
                result.estrategia = "HTML"
        except Exception as exc:  # noqa: BLE001
            result.registrar_error(f"Estrategia HTML (fallback) falló: {exc}")

    if not publicaciones and result.errores:
        result.fallo = True
        return result

    # --- Persistencia ---
    try:
        _persistir(db, publicaciones, result)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        result.fallo = True
        result.registrar_error(f"Error al persistir publicaciones: {exc}")

    return result
