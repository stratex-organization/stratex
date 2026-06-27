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


class NivelRiesgo(str, Enum):
    """Nivel de riesgo/prioridad del asunto para Xignux (Radar Legislativo)."""

    CRITICO = "Crítico"
    ALTO = "Alto"
    MEDIO = "Medio"
    BAJO = "Bajo"
    MONITOREO = "Solo monitoreo"


class HorizonteImpacto(str, Enum):
    """Horizonte temporal estimado en que el asunto impactaría a Xignux."""

    INMEDIATO = "Inmediato"
    CORTO = "Corto plazo"
    MEDIANO = "Mediano plazo"
    LARGO = "Largo plazo"
    INDETERMINADO = "Indeterminado"


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

    # ---- Inteligencia enfocada a Xignux (módulo de Regulación) ----
    autoridad_emisora: str = Field(
        default="",
        description=(
            "Autoridad u órgano que emite el documento (p. ej. CRE, COFEPRIS, "
            "SAT, SENER). Cadena vacía si no se identifica."
        ),
    )
    empresas_afectadas: list[str] = Field(
        default_factory=list,
        description=(
            "Empresas de Xignux potencialmente afectadas (Viakable, Qualtia, "
            "BYDSA). Lista vacía si ninguna se ve afectada. NUNCA incluyas "
            "Prolec GE."
        ),
    )
    productos_afectados: list[str] = Field(
        default_factory=list,
        description="Productos de Xignux potencialmente afectados (si aplica).",
    )
    plantas_afectadas: list[str] = Field(
        default_factory=list,
        description=(
            "Plantas o ubicaciones de Xignux potencialmente afectadas "
            "(p. ej. 'Nuevo León', 'Planta Kalos, Guadalupe')."
        ),
    )
    nivel_riesgo: NivelRiesgo = Field(
        default=NivelRiesgo.MONITOREO,
        description=(
            "Riesgo del asunto para Xignux: Crítico/Alto si amenaza directa y "
            "próxima a una empresa del grupo; Bajo/Solo monitoreo si es "
            "tangencial o meramente informativo."
        ),
    )
    horizonte_impacto: HorizonteImpacto = Field(
        default=HorizonteImpacto.INDETERMINADO,
        description="Horizonte temporal estimado del impacto para Xignux.",
    )
    por_que_importa: str = Field(
        default="",
        description=(
            "¿Por qué le importa a Xignux? Explica el vínculo concreto con sus "
            "empresas, productos, plantas o temas estratégicos. Cadena vacía si "
            "no tiene relación con Xignux."
        ),
    )
    impacto_potencial: str = Field(
        default="",
        description="Impacto potencial concreto para el negocio de Xignux.",
    )
    accion_recomendada: str = Field(
        default="",
        description="Acción institucional recomendada (1-2 oraciones).",
    )
    area_responsable: str = Field(
        default="",
        description=(
            "Área de Xignux sugerida para atender el asunto (p. ej. Asuntos "
            "Corporativos, Cumplimiento, Energía, Calidad/Regulatorio)."
        ),
    )
