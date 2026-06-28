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

from config import (
    CONGRESOS_HOUR_UTC,
    CONGRESOS_WEEKDAY,
    DAILY_PIPELINE_HOUR_UTC,
    ENABLE_DAILY_PIPELINE,
    ENABLE_WEEKLY_CONGRESOS,
)

logger = logging.getLogger(__name__)


def _segundos_hasta(hora_utc: int) -> float:
    """Segundos desde ahora hasta la próxima ocurrencia de `hora_utc:00` (UTC)."""
    ahora = datetime.now(timezone.utc)
    objetivo = ahora.replace(hour=hora_utc % 24, minute=0, second=0, microsecond=0)
    if objetivo <= ahora:
        objetivo += timedelta(days=1)
    return (objetivo - ahora).total_seconds()


def _segundos_hasta_semanal(weekday: int, hora_utc: int) -> float:
    """Segundos hasta el próximo `weekday` (0=lunes) a las `hora_utc:00` UTC."""
    ahora = datetime.now(timezone.utc)
    objetivo = ahora.replace(hour=hora_utc % 24, minute=0, second=0, microsecond=0)
    dias = (weekday % 7 - ahora.weekday()) % 7
    objetivo += timedelta(days=dias)
    if objetivo <= ahora:
        objetivo += timedelta(days=7)
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


def _job_congresos() -> dict:
    """Extrae los 32 congresos y analiza con IA lo nuevo (corre en un hilo)."""
    from database import get_session
    from scrapers import congresos_scraper
    from ai import analyzer

    db = get_session()
    try:
        resultados = congresos_scraper.run_todos(db)
        nuevas = sum(r.nuevas for r in resultados)
        con_datos = sum(1 for r in resultados if r.nuevas or not r.fallo)
        logger.info("Congresos semanal: %d publicaciones nuevas.", nuevas)
        ia = analyzer.procesar_pendientes(db, limite=0)
        return {"nuevas": nuevas, "estados_ok": con_datos, "analizadas": ia.procesadas}
    finally:
        db.close()


async def _loop_congresos() -> None:
    while True:
        espera = _segundos_hasta_semanal(CONGRESOS_WEEKDAY, CONGRESOS_HOUR_UTC)
        logger.info(
            "Congresos semanal: próxima corrida en %.1f h (día %d, %02d:00 UTC).",
            espera / 3600,
            CONGRESOS_WEEKDAY % 7,
            CONGRESOS_HOUR_UTC % 24,
        )
        try:
            await asyncio.sleep(espera)
        except asyncio.CancelledError:
            logger.info("Programador semanal de congresos detenido.")
            raise
        try:
            logger.info("Ejecutando corrida semanal de congresos estatales...")
            await asyncio.to_thread(_job_congresos)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - el programador debe sobrevivir
            logger.exception("La corrida semanal de congresos falló: %s", exc)
        await asyncio.sleep(60)


def estado() -> dict:
    """Estado de los programadores (para exponerlo en la API)."""
    diario = {"activo": False, "hora_utc": None, "proxima_corrida_utc": None}
    if ENABLE_DAILY_PIPELINE:
        proxima = datetime.now(timezone.utc) + timedelta(
            seconds=_segundos_hasta(DAILY_PIPELINE_HOUR_UTC)
        )
        diario = {
            "activo": True,
            "hora_utc": DAILY_PIPELINE_HOUR_UTC % 24,
            "proxima_corrida_utc": proxima.replace(microsecond=0).isoformat(),
        }

    congresos = {"activo": False, "proxima_corrida_utc": None}
    if ENABLE_WEEKLY_CONGRESOS:
        prox_c = datetime.now(timezone.utc) + timedelta(
            seconds=_segundos_hasta_semanal(CONGRESOS_WEEKDAY, CONGRESOS_HOUR_UTC)
        )
        congresos = {
            "activo": True,
            "weekday": CONGRESOS_WEEKDAY % 7,
            "hora_utc": CONGRESOS_HOUR_UTC % 24,
            "proxima_corrida_utc": prox_c.replace(microsecond=0).isoformat(),
        }

    # Compatibilidad: se conservan las claves del pipeline diario en la raíz.
    return {**diario, "diario": diario, "congresos_semanal": congresos}


def iniciar() -> list[asyncio.Task]:
    """Arranca los programadores activos; devuelve la lista de tareas."""
    tareas: list[asyncio.Task] = []
    if ENABLE_DAILY_PIPELINE:
        logger.info("Programador del pipeline diario activado.")
        tareas.append(asyncio.create_task(_loop()))
    else:
        logger.info("Pipeline diario deshabilitado (ENABLE_DAILY_PIPELINE=false).")
    if ENABLE_WEEKLY_CONGRESOS:
        logger.info("Programador semanal de congresos activado.")
        tareas.append(asyncio.create_task(_loop_congresos()))
    else:
        logger.info("Congresos semanal deshabilitado (ENABLE_WEEKLY_CONGRESOS=false).")
    return tareas
