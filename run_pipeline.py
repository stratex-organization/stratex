"""Pipeline diario de StrateX (orquestación completa).

Encadena, de forma segura y secuencial:
  1. Inicializa la BD (tablas + columnas si faltan).
  2. Extracción multi-fuente (ENABLED_SOURCES): DOF + fuentes habilitadas.
  3. Descarga de texto completo de las notas nuevas (si FETCH_FULL_TEXT).
  4. Análisis por IA (DeepSeek) de las publicaciones pendientes.
  5. Envío de alertas de publicaciones relevantes (Slack / correo / consola).
  6. Resumen unificado en consola.

Pensado como punto de entrada para la ejecución programada (cron / launchd).

Uso:
    python run_pipeline.py            # todo el pipeline (IA hasta AI_BATCH_LIMIT)
    python run_pipeline.py 0          # IA de TODAS las pendientes
    python run_pipeline.py --no-ia    # solo extracción + texto completo
"""

from __future__ import annotations

import logging
import sys

from ai import analyzer
from config import DEBUG, DEEPSEEK_API_KEY, FETCH_FULL_TEXT
from database import get_session, init_db
from notifications import alerts
from scrapers import full_text, registry


def _configurar_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _imprimir_resumen(scrapes, full_n, ia, alert) -> None:
    print("\n" + "=" * 64)
    print("  PIPELINE STRATEX — RESUMEN DE LA CORRIDA")
    print("=" * 64)
    print("  [1] Extracción (multi-fuente)")
    for s in scrapes:
        estado = "FALLO" if s.fallo else "ok"
        print(
            f"      {s.fuente:20} {estado:5} | "
            f"nuevas={s.nuevas}  dup={s.duplicadas}  via={s.estrategia}"
        )
    print(f"  [2] Texto completo descargado : {full_n}")
    print("  [3] Análisis por IA (DeepSeek)")
    if ia is None:
        print("      (omitido)")
    elif ia.sin_pendientes:
        print("      Sin publicaciones pendientes de análisis.")
    else:
        print(f"      Procesadas={ia.procesadas}  Fallidas={ia.fallidas}")
    print("  [4] Alertas")
    if alert is None:
        print("      (omitido)")
    else:
        print(
            f"      Enviadas={alert.alertas}  canales={', '.join(alert.canales)}"
        )

    errores = []
    for s in scrapes:
        errores += s.errores
    if ia:
        errores += ia.errores
    if alert:
        errores += alert.errores
    if errores:
        print("  Errores / avisos:")
        for err in errores:
            print(f"    - {err}")
    print("=" * 64 + "\n")


def main(limite_ia: int | None = None, correr_ia: bool = True) -> int:
    _configurar_logging()
    log = logging.getLogger("pipeline")

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo inicializar la base de datos: %s", exc)
        return 1

    db = get_session()
    scrapes = []
    full_n = 0
    ia = None
    alert = None
    try:
        # --- [1] Extracción multi-fuente ---
        log.info("Ejecutando fuentes habilitadas...")
        scrapes = registry.run_all(db)

        # --- [2] Texto completo ---
        if FETCH_FULL_TEXT:
            try:
                full_n = full_text.descargar_pendientes(db)
            except Exception as exc:  # noqa: BLE001
                log.exception("Fallo al descargar texto completo: %s", exc)

        # --- [3] Análisis por IA ---
        if correr_ia:
            if not DEEPSEEK_API_KEY:
                log.warning("DEEPSEEK_API_KEY ausente; se omite el análisis por IA.")
            else:
                try:
                    ia = analyzer.procesar_pendientes(db, limite=limite_ia)
                except Exception as exc:  # noqa: BLE001
                    log.exception("Fallo en el análisis por IA: %s", exc)
                    ia = analyzer.ProcesamientoResult()
                    ia.errores.append(str(exc))

        # --- [4] Alertas ---
        try:
            alert = alerts.enviar_alertas(db)
        except Exception as exc:  # noqa: BLE001
            log.exception("Fallo al enviar alertas: %s", exc)
    finally:
        db.close()

    _imprimir_resumen(scrapes, full_n, ia, alert)

    fallo = all(s.fallo for s in scrapes) if scrapes else True
    return 1 if fallo else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    correr_ia = "--no-ia" not in args
    limite = next((int(a) for a in args if a.lstrip("-").isdigit()), None)
    sys.exit(main(limite_ia=limite, correr_ia=correr_ia))
