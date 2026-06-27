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
├── models.py              # Tabla publicaciones_oficiales
├── main.py                # Entrada: scraping del DOF + resumen
├── process_ai.py          # Entrada: análisis por IA de pendientes
├── run_pipeline.py        # Pipeline completo (fuentes → texto → IA → alertas)
├── scrapers/
│   ├── base.py            # Publicacion, ScrapeResult, persistencia, helpers
│   ├── dof_scraper.py     # Bot híbrido DOF (RSS -> fallback HTML)
│   ├── generic_rss.py     # Scraper genérico RSS/HTML (CNBV, SAT, Banxico…)
│   ├── registry.py        # Registro y ejecución multi-fuente
│   ├── full_text.py       # Descarga del cuerpo completo de las notas
│   └── http_client.py     # Sesión HTTP con bundle TLS para dof.gob.mx
├── ai/
│   ├── schemas.py         # Esquema Pydantic del análisis regulatorio
│   └── analyzer.py        # Cliente DeepSeek + análisis estructurado
├── notifications/
│   └── alerts.py          # Alertas (Slack / correo / consola)
├── api/
│   └── app.py             # API REST + dashboard (FastAPI)
├── scripts/run_daily.sh   # Wrapper para cron/launchd
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
# Requiere DEEPSEEK_API_KEY en .env
python process_ai.py        # procesa hasta AI_BATCH_LIMIT pendientes
python process_ai.py 5      # procesa hasta 5
python process_ai.py 0      # procesa todas las pendientes
```

## Pipeline diario (scraping + IA)
`run_pipeline.py` encadena extracción + análisis en una sola corrida:
```bash
python run_pipeline.py        # scraping + IA (hasta AI_BATCH_LIMIT)
python run_pipeline.py 0      # scraping + IA de todas las pendientes
python run_pipeline.py --no-ia  # solo scraping
```

El pipeline ejecuta, en orden: extracción multi-fuente → descarga de texto
completo → análisis por IA → envío de alertas.

### Automatización
`scripts/run_daily.sh` activa el venv, corre el pipeline y registra la salida en
`logs/`. Para ejecutarlo automáticamente cada día a las 8:00 AM, añade esta línea
con `crontab -e`:
```cron
0 8 * * * /Users/kenethruiz/Desktop/stratex/scripts/run_daily.sh
```

## Multi-fuente
`ENABLED_SOURCES` (en `.env`) controla qué fuentes corren. DOF tiene parsing
dedicado; CNBV, SAT, Banxico y Cámara de Diputados usan el scraper genérico
(`generic_rss`) con endpoints configurables. Cada fuente está aislada: si una
falla, las demás continúan.

> Realidad de los sitios de gobierno MX: gob.mx (CNBV/SAT) está tras un
> challenge anti-bot, Banxico expone su data vía sitio/API propios, y
> diputados.gob.mx puede bloquear por red. La arquitectura está lista; activar
> cada fuente requiere el endpoint correcto, un token, o un proxy/navegador
> headless. La mayoría de estas publicaciones también aparecen en el DOF.

## Texto completo
Con `FETCH_FULL_TEXT=true`, el pipeline descarga el cuerpo íntegro de cada nota
nueva (para el DOF, el contenedor `#DivDetalleNota`) y lo guarda en
`texto_completo`. El analizador de IA prioriza este texto sobre el resumen.

## Alertas
`notifications/alerts.py` detecta publicaciones ya analizadas cuyo
`nivel_relevancia` ∈ `ALERT_NIVELES` (y sector ∈ `ALERT_SECTORES`, si se define)
y aún no alertadas. Notifica por **Slack** (`SLACK_WEBHOOK_URL`) y/o **correo**
(`SMTP_*` + `ALERT_EMAIL_TO`); siempre registra en consola. Marca `alertado` para
no repetir.

## API y Dashboard
```bash
uvicorn api.app:app --port 8000     # luego abre http://127.0.0.1:8000
```
- `GET /` — dashboard HTML con tarjetas, filtros (fuente/sector/relevancia) y búsqueda.
- `GET /api/stats` — conteos agregados.
- `GET /api/publicaciones?fuente=&sector=&nivel=&q=&limit=&offset=` — lista filtrable.
- `GET /api/publicaciones/{id}` — detalle (incluye texto completo).
- `GET /docs` — documentación interactiva (Swagger).
