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

import certifi
import requests

from config import DEFAULT_HEADERS

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


def build_session() -> requests.Session:
    """Crea una `requests.Session` con headers e infraestructura TLS lista."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.verify = CA_BUNDLE
    return session
