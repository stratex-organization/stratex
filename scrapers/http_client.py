"""Cliente HTTP compartido para los scrapers.

El sitio del DOF (dof.gob.mx) presenta una cadena de certificado TLS
**incompleta**: no envía el certificado intermedio de GoDaddy ("Go Daddy
Secure Certificate Authority - G2"). Navegadores y `curl` lo resuelven porque
el sistema operativo tiene ese intermedio, pero `certifi` (que solo trae
certificados raíz) no puede validar la cadena y la verificación TLS falla.

Para mantener la verificación TLS ACTIVA (nunca `verify=False`) y a la vez
funcionar igual en macOS y en Linux/Railway, combinamos el bundle de certifi
con el intermedio faltante (incluido en `certs/dof_intermediate.pem`) en un
único archivo de CAs que pasamos a `requests`.
"""

from __future__ import annotations

import os

import logging

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    DEFAULT_HEADERS,
    SCRAPER_PROXY_URL,
    SCRAPER_PROXY_VERIFY,
    SCRAPINGBEE_COUNTRY,
    SCRAPINGBEE_KEY,
    SCRAPINGBEE_PREMIUM,
)

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CERTS_DIR = os.path.join(_BASE_DIR, "certs")
_INTERMEDIATE = os.path.join(_CERTS_DIR, "dof_intermediate.pem")
_COMBINED = os.path.join(_CERTS_DIR, "_combined_ca.pem")


def _build_ca_bundle() -> str:
    """Devuelve la ruta a un bundle de CAs = certifi + intermedio del DOF.

    Si el intermedio no está disponible, cae limpiamente al bundle de certifi.
    El bundle combinado se regenera si falta o está desactualizado.
    """
    if not os.path.exists(_INTERMEDIATE):
        return certifi.where()

    # Regenera el combinado si no existe o si alguna fuente es más reciente.
    needs_build = not os.path.exists(_COMBINED)
    if not needs_build:
        combined_mtime = os.path.getmtime(_COMBINED)
        for src in (certifi.where(), _INTERMEDIATE):
            if os.path.getmtime(src) > combined_mtime:
                needs_build = True
                break

    if needs_build:
        with open(certifi.where(), "rb") as f:
            roots = f.read()
        with open(_INTERMEDIATE, "rb") as f:
            intermediate = f.read()
        with open(_COMBINED, "wb") as f:
            f.write(roots)
            f.write(b"\n")
            f.write(intermediate)

    return _COMBINED


CA_BUNDLE: str = _build_ca_bundle()


def _scrapingbee_proxy(render_js: bool) -> str:
    """Construye la URL de proxy de ScrapingBee (IP MX + opciones)."""
    opts = [
        f"premium_proxy={'true' if SCRAPINGBEE_PREMIUM else 'false'}",
        f"country_code={SCRAPINGBEE_COUNTRY}",
        f"render_js={'true' if render_js else 'false'}",
    ]
    return f"http://{SCRAPINGBEE_KEY}:{'&'.join(opts)}@proxy.scrapingbee.com:8886"


def build_session(via_scraper: bool = False, render_js: bool = False) -> requests.Session:
    """Crea una `requests.Session` lista para sortear bloqueos comunes.

    Incluye cabeceras de navegador real, verificación TLS con el bundle del DOF,
    y reintentos con backoff (429/5xx).

    Args:
        via_scraper: enruta por ScrapingBee (IP mexicana + bypass de WAF). Solo
            tiene efecto si SCRAPINGBEE_KEY está definida. Úsalo para fuentes
            bloqueadas; consume créditos de la API.
        render_js: pide a ScrapingBee renderizar JavaScript (necesario para
            sitios con challenge JS como gob.mx).

    Precedencia del enrutamiento: ScrapingBee (si via_scraper) > proxy
    residencial (SCRAPER_PROXY_URL) > conexión directa.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    # Reintentos con backoff. En modo scraper NO reintentamos timeouts de
    # lectura (cada reintento consume créditos y el render ya es lento).
    if via_scraper:
        retry = Retry(
            total=1, connect=1, read=0,
            status_forcelist=(429, 500, 502, 503),
            allowed_methods=frozenset(["GET", "HEAD"]),
        )
    else:
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            respect_retry_after_header=True,
        )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    proxy_url: str | None = None
    verify_tls = True

    if via_scraper and SCRAPINGBEE_KEY:
        proxy_url = _scrapingbee_proxy(render_js)
        verify_tls = False  # ScrapingBee intercepta TLS en modo proxy.
        logger.info("Sesión HTTP vía ScrapingBee (MX, render_js=%s).", render_js)
    elif SCRAPER_PROXY_URL:
        proxy_url = SCRAPER_PROXY_URL
        verify_tls = SCRAPER_PROXY_VERIFY
        logger.info("Sesión HTTP usando proxy residencial configurado.")

    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
        if not verify_tls:
            session.verify = False
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        else:
            session.verify = CA_BUNDLE
    else:
        session.verify = CA_BUNDLE

    return session

