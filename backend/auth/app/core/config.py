"""Configuración de la aplicación: todo desde variables de entorno (12-factor).

Funciona igual en localhost y en producción (Railway/Render/Fly) cambiando solo el entorno.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Stratex API"
    ENVIRONMENT: str = "development"  # development | production

    # --- Base de datos ---
    # En local con docker-compose: postgresql+asyncpg://stratex:stratex@db:5432/stratex
    # En producción: la URL que provea el host (Railway/Render). Debe usar el driver asyncpg.
    DATABASE_URL: str = "postgresql+asyncpg://stratex:stratex@localhost:5432/stratex"

    # --- Seguridad / JWT ---
    JWT_SECRET: str = "dev-only-change-me"  # OBLIGATORIO cambiar en producción
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 h

    # --- Contraseña por defecto al registrar (el usuario debe cambiarla en el 1er login) ---
    DEFAULT_PASSWORD: str = "PonchoCabra123"

    # --- CORS (orígenes permitidos del frontend) ---
    # Acepta lista separada por comas: "http://localhost:3000,https://stratex.vercel.app"
    # NoDecode evita que pydantic-settings intente parsear el valor como JSON desde .env.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Brevo (correo transaccional) ---
    BREVO_API_KEY: str | None = None
    EMAIL_FROM: str = "no-reply@stratex.com"
    EMAIL_FROM_NAME: str = "Stratex"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
