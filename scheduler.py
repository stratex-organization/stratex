"""Programador interno del pipeline diario de StrateX.

Corre el pipeline completo (extracción multi-fuente + texto completo + análisis
por IA enfocado a Xignux + alertas) una vez al día, DENTRO del propio servicio
web de FastAPI. Así no se requiere un servicio/cron aparte en Railway.

Se controla con dos variables de entorno (ver config.py):
  - ENABLE_DAILY_PIPELINE (default true)
  - DAILY_PIPELINE_HOUR_UTC (default 13 UTC ≈ 07:00 CDMX)

Para una operación a mayor escala, este programador puede sustituirse por un
servicio Cron dedicado en Railway que ejecute `python run_pipeline.py 0`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from config import DAILY_PIPELINE_HOUR_UTC, ENABLE_DAILY_PIPELINE

logger = logging.getLogger(__name__)


def _segundos_hasta(hora_utc: int) -> float:
    """Segundos desde ahora hasta la próxima ocurrencia de `hora_utc:00` (UTC)."""
    ahora = datetime.now(timezone.utc)
    objetivo = ahora.replace(hour=hora_utc % 24, minute=0, second=0, microsecond=0)
    if objetivo <= ahora:
        objetivo += timedelta(days=1)
    return (objetivo - ahora).total_seconds()


async def _loop() -> None:
    # Import diferido: evita ejecutar la cadena de imports del pipeline al cargar.
    import run_pipeline

    while True:
        espera = _segundos_hasta(DAILY_PIPELINE_HOUR_UTC)
        logger.info(
            "Pipeline diario: próxima corrida en %.1f h (%02d:00 UTC).",
            espera / 3600,
            DAILY_PIPELINE_HOUR_UTC % 24,
        )
        try:
            await asyncio.sleep(espera)
        except asyncio.CancelledError:
            logger.info("Programador del pipeline diario detenido.")
            raise

        try:
            logger.info("Ejecutando pipeline diario programado (IA de todo lo pendiente)...")
            # Se ejecuta en un hilo aparte para no bloquear el event loop.
            await asyncio.to_thread(run_pipeline.main, 0, True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - el programador debe sobrevivir
            logger.exception("El pipeline diario programado falló: %s", exc)

        # Pequeño margen para no volver a disparar dentro del mismo minuto.
        await asyncio.sleep(60)


def estado() -> dict:
    """Estado del pipeline diario (para exponerlo en la API)."""
    if not ENABLE_DAILY_PIPELINE:
        return {"activo": False, "hora_utc": None, "proxima_corrida_utc": None}
    proxima = datetime.now(timezone.utc) + timedelta(
        seconds=_segundos_hasta(DAILY_PIPELINE_HOUR_UTC)
    )
    return {
        "activo": True,
        "hora_utc": DAILY_PIPELINE_HOUR_UTC % 24,
        "proxima_corrida_utc": proxima.replace(microsecond=0).isoformat(),
    }


def iniciar() -> asyncio.Task | None:
    """Arranca el programador diario; devuelve la tarea (o None si está apagado)."""
    if not ENABLE_DAILY_PIPELINE:
        logger.info("Pipeline diario deshabilitado (ENABLE_DAILY_PIPELINE=false).")
        return None
    logger.info("Programador del pipeline diario activado.")
    return asyncio.create_task(_loop())
