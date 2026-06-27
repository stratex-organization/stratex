"""Catálogo de fuentes regulatorias (las "ramas" de monitoreo).

Describe todas las verticales que el producto cubre o aspira a cubrir, agrupadas
por poder/categoría, con su estado operativo real. Sirve para:
  - documentar el alcance del monitoreo,
  - alimentar el panel de "Cobertura regulatoria" del dashboard,
  - registrar qué falta para activar cada rama.

Estados:
  ACTIVA     — extrae datos hoy y aparecen en la base.
  PENDIENTE  — el sitio es alcanzable pero requiere un parser dedicado
               (formularios, API, o navegador headless por ser SPA/JS).
  BLOQUEADA  — anti-bot, 403 o la red rechaza la conexión; requiere navegador
               headless (Playwright) o API oficial para acceder.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FuenteCatalogo:
    clave: str          # identificador
    nombre: str         # nombre legible
    categoria: str      # poder / agrupación
    fuente_db: str      # valor de la columna `fuente` cuando haya datos
    estado: str         # ACTIVA | PENDIENTE | BLOQUEADA
    nota: str           # qué hace falta / cómo se accede


CATALOGO: list[FuenteCatalogo] = [
    # --- Ejecutivo / Diario Oficial ---
    FuenteCatalogo(
        "DOF", "Diario Oficial de la Federación", "Ejecutivo / Diario Oficial",
        "DOF", "ACTIVA", "Sumario diario vía RSS. En operación.",
    ),

    # --- Legislativo ---
    FuenteCatalogo(
        "DIPUTADOS", "Cámara de Diputados — Gaceta Parlamentaria", "Legislativo",
        "Cámara de Diputados", "PENDIENTE",
        "Bypass OK vía ScrapingBee (HTTP 200). La Gaceta usa frames/JS; "
        "requiere parser dedicado para extraer iniciativas.",
    ),
    FuenteCatalogo(
        "SENADO", "Senado de la República — Gaceta", "Legislativo",
        "Senado", "PENDIENTE",
        "Bypass OK vía ScrapingBee (HTTP 200, antes 403). Requiere parser dedicado.",
    ),
    FuenteCatalogo(
        "SIL", "Iniciativas Federales (SIL · Gobernación)", "Legislativo",
        "SIL", "PENDIENTE",
        "Sistema de Información Legislativa. Alcanzable; requiere parser de consultas.",
    ),
    FuenteCatalogo(
        "CONGRESOS", "Congresos Locales (32 legislaturas estatales)", "Legislativo",
        "Congresos Locales", "PENDIENTE",
        "32 sitios heterogéneos; un parser por estado. Esfuerzo incremental.",
    ),

    # --- Judicial ---
    FuenteCatalogo(
        "SCJN", "Suprema Corte (SCJN) — Sentencias, Tesis y Jurisprudencia",
        "Judicial", "SCJN", "PENDIENTE",
        "Semanario Judicial / Buscador Jurídico: SPA + API protegida; requiere headless o API.",
    ),

    # --- Órganos Reguladores ---
    FuenteCatalogo(
        "CNBV", "CNBV — Banca y Valores", "Órganos Reguladores",
        "CNBV", "ACTIVA",
        "Extracción vía ScrapingBee (IP MX + render JS, vence Akamai). En operación.",
    ),
    FuenteCatalogo(
        "SAT", "SAT — Administración Tributaria", "Órganos Reguladores",
        "SAT", "PENDIENTE",
        "Mismo mecanismo gob.mx que CNBV; listo para activar (ENABLED_SOURCES=SAT).",
    ),
    FuenteCatalogo(
        "BANXICO", "Banco de México (Banxico)", "Órganos Reguladores",
        "BANXICO", "PENDIENTE",
        "Alcanzable vía ScrapingBee. Portal JS; requiere parser dedicado.",
    ),
    FuenteCatalogo(
        "IFT", "IFT — Telecomunicaciones", "Órganos Reguladores",
        "IFT", "PENDIENTE",
        "Alcanzable (HTTP 200). Falta parser dedicado.",
    ),
    FuenteCatalogo(
        "CRE", "CRE — Energía", "Órganos Reguladores",
        "CRE", "PENDIENTE",
        "Alcanzable vía ScrapingBee (antes timeout). Falta confirmar endpoint/parser.",
    ),
    FuenteCatalogo(
        "CNH", "CNH — Hidrocarburos", "Órganos Reguladores",
        "CNH", "PENDIENTE",
        "gob.mx, alcanzable vía ScrapingBee+render (vence Akamai). Falta endpoint/parser.",
    ),
    FuenteCatalogo(
        "COFEPRIS", "COFEPRIS — Salud / Sanitario", "Órganos Reguladores",
        "COFEPRIS", "PENDIENTE",
        "gob.mx, alcanzable vía ScrapingBee+render (vence Akamai). Falta endpoint/parser.",
    ),
]


def por_categoria() -> dict[str, list[FuenteCatalogo]]:
    """Agrupa el catálogo por categoría, preservando el orden de aparición."""
    grupos: dict[str, list[FuenteCatalogo]] = {}
    for f in CATALOGO:
        grupos.setdefault(f.categoria, []).append(f)
    return grupos
