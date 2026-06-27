"""Extractor de publicaciones asistido por IA (para sitios heterogéneos).

Los 32 congresos estatales tienen estructuras HTML muy distintas; un parser por
CSS no escala. En su lugar, recolectamos los enlaces de la página y dejamos que
el modelo (DeepSeek) decida cuáles son publicaciones legislativas reales
(boletines, iniciativas, decretos, dictámenes, gacetas, comunicados) y cuáles
son navegación/menús/pie de página.
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from config import AI_BASE_URL, AI_MODEL, DEEPSEEK_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres un extractor experto de publicaciones legislativas de sitios de "
    "congresos estatales mexicanos. Recibes una lista numerada de enlaces "
    "(texto y URL) de una página. Debes devolver SOLO los enlaces que "
    "correspondan a PUBLICACIONES reales: boletines, comunicados, iniciativas, "
    "dictámenes, decretos, leyes, gacetas o acuerdos legislativos. "
    "EXCLUYE navegación, menús, secciones institucionales ('¿Qué es el "
    "Congreso?', 'Junta de Coordinación', 'Diputados por partido', 'Mesa "
    "Directiva', 'Transparencia', 'Contacto'), redes sociales, pie de página y "
    "avisos legales. EXCLUYE también páginas de CATEGORÍA o ÍNDICE genéricas "
    "(p. ej. 'Decretos', 'Leyes y Códigos', 'Iniciativas', 'Acuerdos 2019', "
    "'Orden del Día', 'Proceso de Iniciativas', 'Versiones Estenográficas', "
    "'Reglamento Interior', 'Gaceta'): esas son secciones, no publicaciones. "
    "Incluye SOLO documentos o noticias ESPECÍFICOS: un boletín con titular "
    "concreto, un comunicado fechado, o un decreto/iniciativa con número o tema "
    "específico. Responde EXCLUSIVAMENTE con un objeto JSON válido."
)

MAX_CANDIDATOS = 120

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("Falta DEEPSEEK_API_KEY para el extractor IA.")
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=AI_BASE_URL)
    return _client


def filtrar_publicaciones(
    candidatos: list[dict], fuente: str
) -> list[dict]:
    """Filtra enlaces crudos y devuelve solo las publicaciones reales.

    Args:
        candidatos: lista de dicts {"t": texto, "u": url}.
        fuente: nombre de la fuente (p. ej. "Congreso de Tlaxcala").

    Returns:
        Lista de dicts {"titulo": str, "url": str} con las publicaciones reales.
    """
    if not candidatos:
        return []

    candidatos = candidatos[:MAX_CANDIDATOS]
    lineas = [f"{i}\t{c['t'][:140]}\t{c['u']}" for i, c in enumerate(candidatos)]
    prompt = (
        f"Fuente: {fuente}\n\n"
        "Enlaces (índice, texto, url):\n" + "\n".join(lineas) + "\n\n"
        'Devuelve JSON con esta forma: {"items": [{"titulo": "...", "url": "..."}]}\n'
        "Incluye solo publicaciones legislativas reales (máx. 20, las más "
        "específicas). Usa el texto del enlace como título y su url tal cual. "
        "Si no hay ninguna, devuelve {\"items\": []}."
    )

    client = _get_client()
    completion = client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=2000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(completion.choices[0].message.content or "{}")
    items = data.get("items", [])
    # Validación mínima.
    return [
        {"titulo": it["titulo"].strip(), "url": it["url"].strip()}
        for it in items
        if isinstance(it, dict) and it.get("titulo") and it.get("url")
    ]
