# StrateX — RegTech de Monitoreo Regulatorio (México)

Infraestructura base para monitoreo regulatorio automatizado. Esta primera
entrega incluye el backend, la base de datos y el bot extractor del **Diario
Oficial de la Federación (DOF)**.

## Stack
- Python 3.11+
- PostgreSQL + SQLAlchemy 2.x (ORM)
- `requests`, `beautifulsoup4`, `feedparser` (extracción/parsing)
- `openai` (apuntado a DeepSeek) + `pydantic` (capa de IA)

## Estructura
```
stratex/
├── config.py              # Carga de configuración desde .env
├── database.py            # Engine, sesiones, init_db() + migración aditiva
├── models.py              # Tabla publicaciones_oficiales (+ columnas de IA)
├── main.py                # Entrada: scraping del DOF + resumen
├── process_ai.py          # Entrada: análisis por IA de pendientes
├── scrapers/
│   ├── dof_scraper.py     # Bot híbrido DOF (RSS -> fallback HTML)
│   └── http_client.py     # Sesión HTTP con bundle TLS para dof.gob.mx
├── ai/
│   ├── schemas.py         # Esquema Pydantic del análisis regulatorio
│   └── analyzer.py        # Cliente DeepSeek + análisis estructurado
├── certs/dof_intermediate.pem  # Intermedio TLS que el DOF omite
├── requirements.txt
└── .env.example           # Plantilla de variables de entorno
```

## Puesta en marcha
1. Crea el entorno e instala dependencias:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copia la plantilla de entorno y rellena tus credenciales de PostgreSQL:
   ```bash
   cp .env.example .env
   ```
3. Asegúrate de tener una base de datos PostgreSQL accesible (la de
   `DATABASE_URL`). Por ejemplo, con Docker:
   ```bash
   docker run --name stratex-pg -e POSTGRES_USER=stratex \
     -e POSTGRES_PASSWORD=stratex -e POSTGRES_DB=stratex_db \
     -p 5432:5432 -d postgres:16
   ```
4. Ejecuta el flujo (crea tablas + corre el bot del DOF):
   ```bash
   python main.py
   ```

## Bot del DOF — estrategia híbrida
- **A) RSS** (`DOF_RSS_URL`): consume el feed con `feedparser`, filtra las
  notas del día actual, limpia el resumen e infiere el tipo de edición.
- **B) Fallback HTML** (`DOF_INDEX_URL`): si el RSS falla o no devuelve
  resultados, navega el índice con `requests` + `BeautifulSoup` y extrae los
  enlaces a `nota_detalle.php`.
- **Deduplicación**: una publicación se inserta solo si su `url_origen` no
  existe ya en la base de datos.
- **Políticas de red**: `User-Agent` móvil convencional y retraso aleatorio
  (`SCRAPER_MIN_DELAY`–`SCRAPER_MAX_DELAY` s) entre peticiones HTML.

> Nota: los endpoints públicos del DOF cambian con frecuencia. `DOF_RSS_URL` y
> `DOF_INDEX_URL` son configurables en `.env` para ajustarlos sin tocar código.

## Capa de IA (DeepSeek)
`process_ai.py` toma las publicaciones con `procesado_por_ia = False` y, para
cada una, pide a DeepSeek (`deepseek-chat`, API compatible con OpenAI) un
**análisis estructurado** en JSON mode, validado contra un esquema Pydantic.
Resultados que se guardan en la tabla:
- `resumen_ia` — resumen ejecutivo en español
- `sector` — Financiero, Fiscal, Laboral, Energía, Salud, etc.
- `tipo_documento` — Decreto, Acuerdo, Ley, NOM, Lineamientos…
- `nivel_relevancia` — Alta / Media / Baja
- `entidades` y `palabras_clave` — JSONB
- `analisis_ia` — payload completo (trazabilidad)

```bash
# Requiere ANTHROPIC_API_KEY en .env
python process_ai.py        # procesa hasta AI_BATCH_LIMIT pendientes
python process_ai.py 5      # procesa hasta 5
python process_ai.py 0      # procesa todas las pendientes
```
