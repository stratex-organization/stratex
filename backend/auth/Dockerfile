# Imagen estable con buen soporte de wheels (no usar 3.14 aún por compatibilidad de paquetes).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar dependencias primero (mejor caché de capas)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Copiar el código
COPY . .

EXPOSE 8000

# Aplica migraciones y arranca. $PORT lo inyectan Railway/Render; cae a 8000 en local.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
