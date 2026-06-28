# Stratex — Servicio de Autenticación (`/backend/auth`)

API REST de **autenticación** de Stratex (FastAPI): login, registro y cambio de contraseña. Es un
módulo independiente dentro de `/backend` (separado del backend de contenido de Keneth; ver
`../README.md`). El frontend Next.js lo consume vía su cliente `api()` y nunca accede a la base de
datos directamente.

## Stack

- **FastAPI** + **Uvicorn**
- **PostgreSQL** con **SQLAlchemy 2.0 async** (asyncpg) y **Alembic** para migraciones
- **Pydantic v2** + **pydantic-settings** (config 100% por variables de entorno)
- **JWT** (PyJWT) + hashing **argon2** (`argon2-cffi`)
- **slowapi** (rate limiting) y **httpx** (cliente de Brevo para correos)

## Arquitectura

```
app/
├─ main.py            # FastAPI, CORS, rate limiting, /health
├─ core/             # config, security (hash/JWT), deps, limiter
├─ db/               # engine async + sesión
├─ models/           # SQLAlchemy (User)
├─ schemas/          # Pydantic (auth)
├─ services/         # user_service, email (Brevo)
└─ api/v1/           # routers: auth
alembic/             # migraciones
tests/               # pytest (SQLite async, sin Postgres)
```

## Endpoints (`/v1/auth`)

| Método | Ruta                     | Auth     | Descripción |
|--------|--------------------------|----------|-------------|
| POST   | `/v1/auth/register`      | público  | Alta de usuario (asigna `DEFAULT_PASSWORD`, cambio obligatorio) |
| POST   | `/v1/auth/login`         | público  | Valida credenciales y emite JWT |
| GET    | `/v1/auth/me`            | Bearer   | Usuario actual |
| POST   | `/v1/auth/change-password` | Bearer | Cambia contraseña (1er login) y envía correo de confirmación |

## Correr en local

### Opción A — Docker (recomendada, incluye Postgres)

```bash
docker compose up --build
# API en http://localhost:8000 — docs en http://localhost:8000/docs
```

### Opción B — Python local (requiere un Postgres corriendo)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install .                 # o: pip install -e ".[dev]" para tests
cp .env.example .env          # ajusta DATABASE_URL y JWT_SECRET
alembic upgrade head          # crea las tablas
uvicorn app.main:app --reload
```

> **Nota Python 3.14**: algunos paquetes aún no publican wheels para 3.14. Usa **Python 3.11–3.12**
> en local (la imagen Docker ya fija 3.12).

## Variables de entorno

Ver `.env.example`. Claves: `DATABASE_URL`, `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
`CORS_ORIGINS`, `DEFAULT_PASSWORD`, `BREVO_API_KEY`, `EMAIL_FROM`, `EMAIL_FROM_NAME`.
Si `BREVO_API_KEY` está vacía, los correos se **registran en consola** en lugar de enviarse.

## Tests

```bash
pip install -e ".[dev]"
pytest        # usa SQLite async en memoria; no necesita Postgres
```

## Despliegue (Railway / Render / Fly)

1. Apunta el servicio a este directorio (usa el `Dockerfile`).
2. Provisiona un **PostgreSQL** administrado y define `DATABASE_URL`
   (con el prefijo `postgresql+asyncpg://`).
3. Define `JWT_SECRET`, `CORS_ORIGINS` (incluye el dominio de Vercel), `BREVO_API_KEY`,
   `EMAIL_FROM`, `EMAIL_FROM_NAME`.
4. El contenedor corre `alembic upgrade head` y luego `uvicorn` automáticamente.

## Seguridad

Hashing argon2, JWT firmado, CORS restringido, rate limiting en login, validación estricta de
entrada y mensajes de error genéricos. **Pendiente (futuro):** refresh tokens, bloqueo por intentos
fallidos y recuperación de contraseña por correo.
