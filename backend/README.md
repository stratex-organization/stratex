# Stratex — Backend

Este directorio agrupa los servicios de backend de Stratex. Está organizado en **módulos
independientes** para separar responsabilidades y evitar mezclar código de distintas áreas del
equipo.

## Módulos

| Carpeta | Responsable | Descripción |
|---------|-------------|-------------|
| [`auth/`](auth/) | Diego | Servicio de **autenticación** (login, registro, cambio de contraseña). FastAPI + PostgreSQL. Es lo que consume el frontend para el acceso. |
| _(por definir)_ | Keneth | Backend de **contenido**: extracción/scraping de datos gubernamentales (DOF/IA). Se integrará aquí como su propio módulo. |

> Cada módulo es autocontenido (su propio `pyproject.toml`, migraciones y `Dockerfile`), de modo
> que se desarrollan y despliegan sin pisarse. Si más adelante el equipo decide unificarlos en un
> solo servicio FastAPI, cada uno aporta su router bajo `/v1/...`.

## Servicio de autenticación

Toda la documentación, comandos y variables de entorno están en **[`auth/README.md`](auth/README.md)**.

Arranque rápido:

```bash
cd auth
docker compose up --build        # API en http://localhost:8000 (docs en /docs)
```
