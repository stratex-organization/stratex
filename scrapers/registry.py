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
    CNH_INDEX_URL,
    COFEPRIS_INDEX_URL,
    CRE_INDEX_URL,
    DIPUTADOS_INDEX_URL,
    DIPUTADOS_RSS_URL,
    ENABLED_SOURCES,
    SAT_INDEX_URL,
    SAT_RSS_URL,
    SENADO_INDEX_URL,
)
from scrapers import dof_scraper, generic_rss
from scrapers.base import ScrapeResult
from scrapers.generic_rss import FuenteConfig

logger = logging.getLogger(__name__)

# Configuración de las fuentes genéricas (todas menos DOF).
# via_scraper=True enruta por ScrapingBee (IP MX); render_js=True para gob.mx/SPAs.
_GENERIC_SOURCES: dict[str, FuenteConfig] = {
    "CNBV": FuenteConfig(
        "CNBV", index_url=CNBV_INDEX_URL, via_scraper=True, render_js=True
    ),
    "SAT": FuenteConfig(
        "SAT", index_url=SAT_INDEX_URL, via_scraper=True, render_js=True
    ),
    "CNH": FuenteConfig(
        "CNH", index_url=CNH_INDEX_URL, via_scraper=True, render_js=True
    ),
    "COFEPRIS": FuenteConfig(
        # Sin render: la página es muy pesada y el render hace timeout.
        "COFEPRIS", index_url=COFEPRIS_INDEX_URL, via_scraper=True, render_js=False
    ),
    "CRE": FuenteConfig(
        "CRE", index_url=CRE_INDEX_URL, via_scraper=True, render_js=True
    ),
    "BANXICO": FuenteConfig(
        "BANXICO", index_url=BANXICO_INDEX_URL, via_scraper=True, render_js=True
    ),
    "DIPUTADOS": FuenteConfig(
        "Cámara de Diputados", index_url=DIPUTADOS_INDEX_URL, via_scraper=True
    ),
    "SENADO": FuenteConfig(
        "Senado", index_url=SENADO_INDEX_URL, via_scraper=True
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
