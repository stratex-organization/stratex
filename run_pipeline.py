"""Pipeline diario de StrateX: extracción + análisis por IA, en una corrida.

Encadena, de forma segura y secuencial:
  1. Inicializa la BD (tablas + columnas de IA si faltan).
  2. Ejecuta el bot del DOF (RSS -> fallback HTML) con deduplicación.
  3. Analiza con IA (DeepSeek) las publicaciones pendientes.
  4. Imprime un resumen unificado.

Pensado como punto de entrada para la ejecución programada (cron / launchd).

Uso:
    python run_pipeline.py            # scraping + IA (hasta AI_BATCH_LIMIT)
    python run_pipeline.py 0          # scraping + IA de TODAS las pendientes
    python run_pipeline.py --no-ia    # solo scraping
"""

from __future__ import annotations

import logging
import sys

from ai import analyzer
from config import DEBUG, DEEPSEEK_API_KEY
from database import get_session, init_db
from scrapers import dof_scraper


def _configurar_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _imprimir_resumen(
    scrape: dof_scraper.ScrapeResult,
    ia: analyzer.ProcesamientoResult | None,
) -> None:
    print("\n" + "=" * 60)
    print("  PIPELINE STRATEX — RESUMEN DE LA CORRIDA")
    print("=" * 60)
    print("  [1] Extracción (DOF)")
    print(f"      Estrategia utilizada : {scrape.estrategia}")
    print(f"      Publicaciones nuevas : {scrape.nuevas}")
    print(f"      Duplicadas ignoradas : {scrape.duplicadas}")
    print(f"      Fallo de scraping    : {'SÍ' if scrape.fallo else 'no'}")
    print("  [2] Análisis por IA (DeepSeek)")
    if ia is None:
        print("      (omitido)")
    elif ia.sin_pendientes:
        print("      Sin publicaciones pendientes de análisis.")
    else:
        print(f"      Procesadas           : {ia.procesadas}")
        print(f"      Fallidas             : {ia.fallidas}")
    errores = list(scrape.errores) + (list(ia.errores) if ia else [])
    if errores:
        print("  Errores:")
        for err in errores:
            print(f"    - {err}")
    print("=" * 60 + "\n")


def main(limite_ia: int | None = None, correr_ia: bool = True) -> int:
    _configurar_logging()
    log = logging.getLogger("pipeline")

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo inicializar la base de datos: %s", exc)
        return 1

    db = get_session()
    try:
        # --- [1] Extracción ---
        log.info("Ejecutando bot del DOF...")
        try:
            scrape = dof_scraper.run(db)
        except Exception as exc:  # noqa: BLE001
            log.exception("Fallo inesperado en el scraping: %s", exc)
            scrape = dof_scraper.ScrapeResult(fallo=True)
            scrape.errores.append(str(exc))

        # --- [2] Análisis por IA ---
        ia: analyzer.ProcesamientoResult | None = None
        if correr_ia:
            if not DEEPSEEK_API_KEY:
                log.warning("DEEPSEEK_API_KEY ausente; se omite el análisis por IA.")
            else:
                try:
                    ia = analyzer.procesar_pendientes(db, limite=limite_ia)
                except Exception as exc:  # noqa: BLE001
                    log.exception("Fallo inesperado en el análisis por IA: %s", exc)
                    ia = analyzer.ProcesamientoResult()
                    ia.errores.append(str(exc))
    finally:
        db.close()

    _imprimir_resumen(scrape, ia)
    fallo = scrape.fallo or bool(ia and ia.fallidas and not ia.procesadas)
    return 1 if fallo else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    correr_ia = "--no-ia" not in args
    limite = None
    for a in args:
        if a.lstrip("-").isdigit():
            limite = int(a)
            break
    sys.exit(main(limite_ia=limite, correr_ia=correr_ia))
