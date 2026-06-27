"""Esquema estructurado del análisis regulatorio producido por Claude.

Se usa con `client.messages.parse(output_format=...)` para garantizar que la
respuesta del modelo siempre valide contra esta estructura (JSON válido).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Sector(str, Enum):
    """Sectores regulatorios relevantes para el monitoreo en México."""

    FINANCIERO = "Financiero/Bancario"
    FISCAL = "Fiscal/Tributario"
    LABORAL = "Laboral"
    ENERGIA = "Energía"
    SALUD = "Salud"
    TELECOMUNICACIONES = "Telecomunicaciones"
    COMERCIO_EXTERIOR = "Comercio Exterior"
    MEDIO_AMBIENTE = "Medio Ambiente"
    DATOS_PERSONALES = "Datos Personales/Privacidad"
    COMPETENCIA = "Competencia Económica"
    ADMINISTRATIVO = "Administrativo/Gobierno"
    OTRO = "Otro"


class NivelRelevancia(str, Enum):
    """Relevancia regulatoria estimada de la publicación."""

    ALTA = "Alta"
    MEDIA = "Media"
    BAJA = "Baja"


class AnalisisRegulatorio(BaseModel):
    """Resultado del análisis de una publicación oficial."""

    resumen: str = Field(
        description=(
            "Resumen ejecutivo en español (2-4 oraciones) del contenido y "
            "propósito de la publicación, en lenguaje claro."
        )
    )
    sector: Sector = Field(
        description="Sector regulatorio principal al que pertenece la publicación."
    )
    tipo_documento: str = Field(
        description=(
            "Tipo de instrumento jurídico: p. ej. Decreto, Acuerdo, Ley, "
            "Reglamento, Norma Oficial Mexicana, Lineamientos, Aviso, Oficio."
        )
    )
    nivel_relevancia: NivelRelevancia = Field(
        description=(
            "Relevancia regulatoria: Alta si crea/modifica obligaciones de "
            "cumplimiento amplias; Media si afecta a un sector acotado; Baja "
            "si es informativo o administrativo de bajo impacto."
        )
    )
    entidades: list[str] = Field(
        description=(
            "Dependencias, organismos o sujetos obligados mencionados "
            "(p. ej. 'SHCP', 'CNBV', 'SAT', 'IMSS')."
        )
    )
    palabras_clave: list[str] = Field(
        description="3 a 8 palabras o frases clave que describen el contenido."
    )
    impacto: str = Field(
        description=(
            "Una oración sobre a quién impacta y qué acción de cumplimiento "
            "podría requerir."
        )
    )
