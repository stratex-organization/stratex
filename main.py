"""Punto de entrada de StrateX RegTech.

Flujo secuencial:
  1. Inicializa la conexión y crea las tablas si no existen.
  2. Ejecuta el bot del DOF de forma segura (captura de excepciones).
  3. Muestra un resumen del resultado en la terminal.
"""

from __future__ import annotations

import logging
import sys

from config import DEBUG
from database import get_session, init_db
from scrapers import dof_scraper


def _configurar_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _imprimir_resumen(result: dof_scraper.ScrapeResult) -> None:
    print("\n" + "=" * 60)
    print("  RESUMEN DE EXTRACCIÓN — Diario Oficial de la Federación")
    print("=" * 60)
    print(f"  Estrategia utilizada : {result.estrategia}")
    print(f"  Publicaciones nuevas : {result.nuevas}")
    print(f"  Duplicadas ignoradas : {result.duplicadas}")
    print(f"  Fallo de scraping    : {'SÍ' if result.fallo else 'no'}")
    if result.errores:
        print("  Errores:")
        for err in result.errores:
            print(f"    - {err}")
    print("=" * 60 + "\n")


def main() -> int:
    _configurar_logging()
    log = logging.getLogger("main")

    # 1. Base de datos
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo inicializar la base de datos: %s", exc)
        return 1

    # 2. Ejecución segura del bot del DOF
    session = get_session()
    try:
        log.info("Ejecutando bot del DOF...")
        result = dof_scraper.run(session)
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo inesperado durante el scraping del DOF: %s", exc)
        result = dof_scraper.ScrapeResult(fallo=True)
        result.errores.append(str(exc))
    finally:
        session.close()

    # 3. Resumen
    _imprimir_resumen(result)
    return 1 if result.fallo else 0


if __name__ == "__main__":
    sys.exit(main())
