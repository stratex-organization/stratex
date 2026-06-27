"""Carga centralizada de configuración desde el entorno (.env)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Carga el archivo .env si existe (no falla si no está presente).
load_dotenv()


def _build_database_url() -> str:
    """Devuelve la cadena de conexión a PostgreSQL.

    Prioriza DATABASE_URL; si no está definida, la construye a partir de
    las piezas individuales (POSTGRES_USER, POSTGRES_PASSWORD, etc.).
    """
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    user = os.getenv("POSTGRES_USER", "stratex")
    password = os.getenv("POSTGRES_PASSWORD", "stratex")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "stratex_db")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL: str = _build_database_url()

# --- Scraper DOF ---
DOF_RSS_URL: str = os.getenv(
    "DOF_RSS_URL", "https://www.dof.gob.mx/sumario.xml"
)
DOF_INDEX_URL: str = os.getenv("DOF_INDEX_URL", "https://www.dof.gob.mx/")

# --- Capa de IA (DeepSeek; API compatible con OpenAI) ---
DEEPSEEK_API_KEY: str | None = os.getenv("DEEPSEEK_API_KEY")
# Endpoint compatible con OpenAI de DeepSeek.
AI_BASE_URL: str = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
# Modelo: "deepseek-chat" (V3, rápido) o "deepseek-reasoner" (R1, razonamiento).
AI_MODEL: str = os.getenv("AI_MODEL", "deepseek-chat")
# Cuántas publicaciones procesar por corrida (0 = sin límite).
AI_BATCH_LIMIT: int = int(os.getenv("AI_BATCH_LIMIT", "25"))

# --- Red ---
SCRAPER_MIN_DELAY: float = float(os.getenv("SCRAPER_MIN_DELAY", "1"))
SCRAPER_MAX_DELAY: float = float(os.getenv("SCRAPER_MAX_DELAY", "3"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}

# User-Agent convencional (móvil) para reducir bloqueos del servidor.
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}
