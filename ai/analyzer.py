"""Analizador regulatorio con DeepSeek (API compatible con OpenAI).

Toma publicaciones oficiales sin procesar y produce, para cada una, un análisis
estructurado (resumen, sector, relevancia, entidades, palabras clave). Se usa el
"JSON mode" de DeepSeek para forzar una respuesta JSON, que luego se valida
contra el esquema Pydantic `AnalisisRegulatorio`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.schemas import AnalisisRegulatorio, NivelRelevancia, Sector
from config import AI_BASE_URL, AI_BATCH_LIMIT, AI_MODEL, DEEPSEEK_API_KEY
from models import PublicacionOficial

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres un analista regulatorio experto en el marco jurídico mexicano. "
    "Analizas publicaciones oficiales (decretos, acuerdos, leyes, normas) y "
    "produces análisis estructurados, precisos y en español, útiles para un "
    "equipo de cumplimiento normativo. Sé objetivo y conservador: si la "
    "información es insuficiente, refléjalo en el nivel de relevancia. "
    "Respondes EXCLUSIVAMENTE con un objeto JSON válido, sin texto adicional."
)


@dataclass
class ProcesamientoResult:
    """Resumen del resultado de una corrida de procesamiento por IA."""

    procesadas: int = 0
    fallidas: int = 0
    sin_pendientes: bool = False
    errores: list[str] = field(default_factory=list)

    def registrar_error(self, msg: str) -> None:
        logger.error(msg)
        self.errores.append(msg)


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Devuelve un cliente OpenAI->DeepSeek reutilizable (lazy)."""
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError(
                "Falta DEEPSEEK_API_KEY. Defínela en tu archivo .env "
                "para habilitar el análisis con IA."
            )
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=AI_BASE_URL)
    return _client


def _instrucciones_formato() -> str:
    """Describe el JSON esperado (con valores válidos de los enums)."""
    sectores = " | ".join(s.value for s in Sector)
    niveles = " | ".join(n.value for n in NivelRelevancia)
    return (
        "Devuelve un objeto JSON con EXACTAMENTE estos campos:\n"
        "{\n"
        '  "resumen": "resumen ejecutivo en español, 2-4 oraciones",\n'
        f'  "sector": "uno de: {sectores}",\n'
        '  "tipo_documento": "p.ej. Decreto, Acuerdo, Ley, Reglamento, NOM, '
        'Lineamientos, Aviso, Oficio",\n'
        f'  "nivel_relevancia": "uno de: {niveles}",\n'
        '  "entidades": ["dependencias o sujetos obligados, p.ej. SHCP, CNBV, SAT"],\n'
        '  "palabras_clave": ["3 a 8 palabras o frases clave"],\n'
        '  "impacto": "una oración: a quién impacta y qué acción de cumplimiento '
        'podría requerir"\n'
        "}\n"
        "No incluyas ningún texto fuera del objeto JSON."
    )


def _construir_prompt(pub: PublicacionOficial) -> str:
    """Arma el mensaje de usuario con los datos disponibles de la publicación."""
    partes = [
        f"Fuente: {pub.fuente}",
        f"Fecha de publicación: {pub.fecha_publicacion}",
        f"Tipo de edición: {pub.tipo_edicion or 'N/D'}",
        f"Título / Sección: {pub.titulo}",
    ]
    if pub.texto_limpio and pub.texto_limpio.strip() != (pub.titulo or "").strip():
        partes.append(f"Contenido / Contexto: {pub.texto_limpio}")
    partes.append(f"URL de origen: {pub.url_origen}")
    return (
        "Analiza la siguiente publicación oficial:\n\n"
        + "\n".join(partes)
        + "\n\n"
        + _instrucciones_formato()
    )


def _coaccionar_enums(data: dict) -> dict:
    """Mapea valores de enum no reconocidos a un valor por defecto seguro."""
    sectores = {s.value for s in Sector}
    niveles = {n.value for n in NivelRelevancia}
    if data.get("sector") not in sectores:
        data["sector"] = Sector.OTRO.value
    if data.get("nivel_relevancia") not in niveles:
        data["nivel_relevancia"] = NivelRelevancia.MEDIA.value
    return data


def analizar_publicacion(pub: PublicacionOficial) -> AnalisisRegulatorio:
    """Llama a DeepSeek y devuelve el análisis estructurado de una publicación."""
    client = _get_client()
    completion = client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=1500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _construir_prompt(pub)},
        ],
    )
    contenido = completion.choices[0].message.content or "{}"
    data = _coaccionar_enums(json.loads(contenido))
    return AnalisisRegulatorio.model_validate(data)


def _aplicar_analisis(pub: PublicacionOficial, analisis: AnalisisRegulatorio) -> None:
    """Vuelca el análisis estructurado en las columnas del registro."""
    pub.resumen_ia = analisis.resumen
    pub.sector = analisis.sector.value
    pub.tipo_documento = analisis.tipo_documento
    pub.nivel_relevancia = analisis.nivel_relevancia.value
    pub.entidades = analisis.entidades
    pub.palabras_clave = analisis.palabras_clave
    pub.analisis_ia = analisis.model_dump(mode="json")
    pub.procesado_por_ia = True
    pub.procesado_en = datetime.now(timezone.utc)


def procesar_pendientes(
    db: Session, limite: int | None = None
) -> ProcesamientoResult:
    """Procesa con IA las publicaciones aún no analizadas.

    Args:
        db: sesión activa de SQLAlchemy.
        limite: máximo de publicaciones a procesar (None usa AI_BATCH_LIMIT;
            0 procesa todas las pendientes).

    Returns:
        ProcesamientoResult con el resumen de la corrida.
    """
    result = ProcesamientoResult()

    if limite is None:
        limite = AI_BATCH_LIMIT

    consulta = (
        select(PublicacionOficial)
        .where(PublicacionOficial.procesado_por_ia.is_(False))
        .order_by(PublicacionOficial.creado_en)
    )
    if limite and limite > 0:
        consulta = consulta.limit(limite)

    pendientes = list(db.scalars(consulta))
    if not pendientes:
        result.sin_pendientes = True
        logger.info("No hay publicaciones pendientes de análisis por IA.")
        return result

    logger.info("Procesando %d publicaciones con IA (%s)...", len(pendientes), AI_MODEL)

    for pub in pendientes:
        try:
            analisis = analizar_publicacion(pub)
            _aplicar_analisis(pub, analisis)
            db.commit()
            result.procesadas += 1
            logger.info(
                "OK [%s | %s] %s",
                analisis.sector.value,
                analisis.nivel_relevancia.value,
                pub.titulo[:60],
            )
        except Exception as exc:  # noqa: BLE001 - aislamos el fallo por registro
            db.rollback()
            result.fallidas += 1
            result.registrar_error(f"Fallo al analizar {pub.url_origen}: {exc}")

    return result
