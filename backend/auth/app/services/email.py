"""Cliente de correo transaccional (Brevo).

Si no hay BREVO_API_KEY configurada, registra el correo en consola en vez de fallar.
Esto permite probar el flujo completo antes de configurar las claves y el DNS.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("stratex.email")

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


async def _send(*, to_email: str, to_name: str, subject: str, html: str) -> None:
    if not settings.BREVO_API_KEY:
        logger.warning(
            "BREVO_API_KEY no configurada. Correo NO enviado (modo local).\n"
            "  Para: %s <%s>\n  Asunto: %s",
            to_name,
            to_email,
            subject,
        )
        return

    payload = {
        "sender": {"email": settings.EMAIL_FROM, "name": settings.EMAIL_FROM_NAME},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html,
    }
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(BREVO_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as exc:  # no romper el flujo por un fallo de correo
        logger.error("Error enviando correo vía Brevo a %s: %s", to_email, exc)


async def send_password_changed_email(*, to_email: str, nombre: str) -> None:
    """Confirma al usuario que su contraseña fue actualizada."""
    subject = "Tu contraseña de Stratex fue actualizada"
    html = (
        f"<p>Hola {nombre},</p>"
        "<p>Te confirmamos que la contraseña de tu cuenta de <strong>Stratex</strong> "
        "se actualizó correctamente.</p>"
        "<p>Si no realizaste este cambio, contacta de inmediato al administrador.</p>"
        "<p>— Equipo Stratex</p>"
    )
    await _send(to_email=to_email, to_name=nombre, subject=subject, html=html)
