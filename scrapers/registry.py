"""Registro de fuentes y ejecución multi-fuente.

DOF tiene parsing dedicado (`dof_scraper`); el resto usan el scraper genérico
(`generic_rss`) con su `FuenteConfig`. `ENABLED_SOURCES` (en .env) controla qué
fuentes corren en el pipeline.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from config import (
    BANXICO_INDEX_URL,
    BANXICO_RSS_URL,
    CNBV_INDEX_URL,
    CNBV_RSS_URL,
    DIPUTADOS_INDEX_URL,
    DIPUTADOS_RSS_URL,
    ENABLED_SOURCES,
    SAT_INDEX_URL,
    SAT_RSS_URL,
)
from scrapers import dof_scraper, generic_rss
from scrapers.base import ScrapeResult
from scrapers.generic_rss import FuenteConfig

logger = logging.getLogger(__name__)

# Configuración de las fuentes genéricas (todas menos DOF).
_GENERIC_SOURCES: dict[str, FuenteConfig] = {
    "CNBV": FuenteConfig("CNBV", rss_url=CNBV_RSS_URL, index_url=CNBV_INDEX_URL),
    "SAT": FuenteConfig("SAT", rss_url=SAT_RSS_URL, index_url=SAT_INDEX_URL),
    "BANXICO": FuenteConfig(
        "BANXICO", rss_url=BANXICO_RSS_URL, index_url=BANXICO_INDEX_URL
    ),
    "DIPUTADOS": FuenteConfig(
        "Cámara de Diputados",
        rss_url=DIPUTADOS_RSS_URL,
        index_url=DIPUTADOS_INDEX_URL,
    ),
}


def run_all(db: Session, hoy: date | None = None) -> list[ScrapeResult]:
    """Ejecuta todas las fuentes habilitadas en ENABLED_SOURCES."""
    resultados: list[ScrapeResult] = []

    for nombre in ENABLED_SOURCES:
        if nombre == "DOF":
            resultados.append(dof_scraper.run(db, hoy=hoy))
        elif nombre in _GENERIC_SOURCES:
            resultados.append(generic_rss.run(db, _GENERIC_SOURCES[nombre], hoy=hoy))
        else:
            logger.warning("Fuente desconocida en ENABLED_SOURCES: %s", nombre)

    return resultados
