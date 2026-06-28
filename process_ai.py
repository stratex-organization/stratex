"""Procesamiento por IA de las publicaciones pendientes.

Flujo:
  1. Inicializa la BD (crea tablas y columnas de IA si faltan).
  2. Analiza con Claude las publicaciones con procesado_por_ia = False.
  3. Muestra un resumen del resultado en la terminal.

Uso:
    python process_ai.py            # procesa hasta AI_BATCH_LIMIT pendientes
    python process_ai.py 5          # procesa hasta 5
    python process_ai.py 0          # procesa todas las pendientes
"""

from __future__ import annotations

import logging
import sys

from ai import analyzer
from config import DEEPSEEK_API_KEY, DEBUG
from database import get_session, init_db


def _configurar_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _imprimir_resumen(result: analyzer.ProcesamientoResult) -> None:
    print("\n" + "=" * 60)
    print("  RESUMEN DE ANÁLISIS POR IA (DeepSeek)")
    print("=" * 60)
    if result.sin_pendientes:
        print("  No había publicaciones pendientes de análisis.")
    else:
        print(f"  Procesadas correctamente : {result.procesadas}")
        print(f"  Fallidas                 : {result.fallidas}")
    if result.errores:
        print("  Errores:")
        for err in result.errores:
            print(f"    - {err}")
    print("=" * 60 + "\n")


def main(limite: int | None = None) -> int:
    _configurar_logging()
    log = logging.getLogger("process_ai")

    if not DEEPSEEK_API_KEY:
        log.error(
            "Falta DEEPSEEK_API_KEY en el entorno (.env). "
            "Añádela para habilitar el análisis con IA."
        )
        return 1

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo inicializar la base de datos: %s", exc)
        return 1

    db = get_session()
    try:
        result = analyzer.procesar_pendientes(db, limite=limite)
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo inesperado durante el procesamiento por IA: %s", exc)
        return 1
    finally:
        db.close()

    _imprimir_resumen(result)
    return 1 if result.fallidas and not result.procesadas else 0


if __name__ == "__main__":
    arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(main(arg))
