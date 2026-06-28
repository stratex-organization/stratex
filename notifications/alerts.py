"""Alertas de publicaciones regulatorias relevantes.

Busca publicaciones ya analizadas por IA cuyo nivel de relevancia y sector
coinciden con la política de vigilancia (ALERT_NIVELES / ALERT_SECTORES) y que
aún no han sido alertadas (`alertado = False`). Notifica por Slack y/o correo
si están configurados; siempre registra en consola como respaldo. Marca cada
publicación como alertada para no repetir.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import (
    ALERT_EMAIL_FROM,
    ALERT_EMAIL_TO,
    ALERT_NIVELES,
    ALERT_SECTORES,
    SLACK_WEBHOOK_URL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from models import PublicacionOficial

logger = logging.getLogger(__name__)


@dataclass
class AlertResult:
    """Resumen del envío de alertas."""

    alertas: int = 0
    canales: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def _canales_activos() -> list[str]:
    canales = ["consola"]
    if SLACK_WEBHOOK_URL:
        canales.append("slack")
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD and ALERT_EMAIL_TO:
        canales.append("email")
    return canales


def _formatear(pub: PublicacionOficial) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) para una publicación."""
    asunto = f"[StrateX] Alerta {pub.nivel_relevancia} · {pub.sector} · {pub.fuente}"
    cuerpo = (
        f"Fuente: {pub.fuente}\n"
        f"Fecha: {pub.fecha_publicacion}\n"
        f"Sector: {pub.sector}  |  Relevancia: {pub.nivel_relevancia}\n"
        f"Tipo: {pub.tipo_documento}\n\n"
        f"Título: {pub.titulo}\n\n"
        f"Resumen: {pub.resumen_ia}\n\n"
        f"Enlace: {pub.url_origen}\n"
    )
    return asunto, cuerpo


def _enviar_slack(asunto: str, cuerpo: str) -> None:
    payload = {"text": f"*{asunto}*\n{cuerpo}"}
    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=15)
    resp.raise_for_status()


def _enviar_email(asunto: str, cuerpo: str) -> None:
    msg = MIMEText(cuerpo, _charset="utf-8")
    msg["Subject"] = asunto
    msg["From"] = ALERT_EMAIL_FROM or SMTP_USER
    msg["To"] = ", ".join(ALERT_EMAIL_TO)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def enviar_alertas(db: Session) -> AlertResult:
    """Envía alertas para las publicaciones relevantes aún no notificadas."""
    result = AlertResult(canales=_canales_activos())

    consulta = (
        select(PublicacionOficial)
        .where(PublicacionOficial.procesado_por_ia.is_(True))
        .where(PublicacionOficial.alertado.is_(False))
        .where(PublicacionOficial.nivel_relevancia.in_(ALERT_NIVELES))
    )
    if ALERT_SECTORES:
        consulta = consulta.where(PublicacionOficial.sector.in_(ALERT_SECTORES))

    pendientes = list(db.scalars(consulta))
    if not pendientes:
        logger.info("No hay publicaciones nuevas que ameriten alerta.")
        return result

    logger.info(
        "Enviando %d alertas por: %s", len(pendientes), ", ".join(result.canales)
    )

    for pub in pendientes:
        asunto, cuerpo = _formatear(pub)

        # Consola (siempre).
        logger.warning("ALERTA → %s | %s", asunto, pub.titulo[:60])

        if SLACK_WEBHOOK_URL:
            try:
                _enviar_slack(asunto, cuerpo)
            except Exception as exc:  # noqa: BLE001
                result.errores.append(f"Slack falló ({pub.url_origen}): {exc}")

        if "email" in result.canales:
            try:
                _enviar_email(asunto, cuerpo)
            except Exception as exc:  # noqa: BLE001
                result.errores.append(f"Email falló ({pub.url_origen}): {exc}")

        pub.alertado = True
        db.commit()
        result.alertas += 1

    for err in result.errores:
        logger.error(err)

    return result
