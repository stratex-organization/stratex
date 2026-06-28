"""API REST + dashboard de StrateX (FastAPI).

Expone las publicaciones analizadas con filtros por fuente, sector, relevancia
y búsqueda de texto, estadísticas agregadas y **acciones** (disparar scraping,
análisis por IA y marcar publicaciones). La raíz ("/") sirve un dashboard HTML
autocontenido que consume estos endpoints.

Autenticación: las acciones (POST/PATCH) exigen el header `X-API-Key` cuando
`API_KEY` está definida en el entorno. La lectura (GET) es pública.

CORS: configurable con `CORS_ORIGINS` (coma). Permite que un frontend en otro
dominio/puerto consuma la API.

Ejecutar:
    uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

import logging
import threading
import uuid as uuidlib
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func, select, update

import scheduler
from ai import analyzer
from config import API_KEY, CORS_ORIGINS, DEEPSEEK_API_KEY, FETCH_FULL_TEXT
from database import get_session, init_db
from models import EmpresaXignux, PublicacionOficial as P
from scrapers import full_text, registry
from scrapers.catalog import por_categoria
from scrapers.congresos_scraper import NOMBRES_CONGRESOS

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garantiza que el esquema/columnas existan al levantar la API.
    init_db()
    # Arranca los programadores: pipeline diario + congresos semanal.
    tareas = scheduler.iniciar()
    try:
        yield
    finally:
        for t in tareas or []:
            t.cancel()


app = FastAPI(title="StrateX RegTech API", version="1.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
#  Autenticación de acciones                                                   #
# --------------------------------------------------------------------------- #
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Exige X-API-Key en endpoints de acción si API_KEY está configurada."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="API key inválida o ausente (header X-API-Key).",
        )


# --------------------------------------------------------------------------- #
#  Gestor de trabajos en segundo plano (scraping / IA)                        #
# --------------------------------------------------------------------------- #
_jobs_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {
    "scrape": {"estado": "idle", "resultado": None, "error": None},
    "ia": {"estado": "idle", "resultado": None, "error": None},
}


def _ejecutar_job(nombre: str, fn) -> None:
    """Corre la función de un trabajo con su propia sesión y guarda el estado."""
    db = get_session()
    try:
        resultado = fn(db)
        estado = {"estado": "done", "resultado": resultado, "error": None}
    except Exception as exc:  # noqa: BLE001 - lo reflejamos en el estado del job
        logger.exception("El trabajo '%s' falló: %s", nombre, exc)
        estado = {"estado": "error", "resultado": None, "error": str(exc)}
    finally:
        db.close()
    with _jobs_lock:
        _jobs[nombre] = estado


def _lanzar_job(nombre: str, fn, background: BackgroundTasks) -> None:
    """Marca el trabajo como en ejecución y lo agenda; 409 si ya corre."""
    with _jobs_lock:
        if _jobs.get(nombre, {}).get("estado") == "running":
            raise HTTPException(
                status_code=409,
                detail=f"El trabajo '{nombre}' ya está en ejecución.",
            )
        _jobs[nombre] = {"estado": "running", "resultado": None, "error": None}
    background.add_task(_ejecutar_job, nombre, fn)


def _job_scrape(db) -> dict[str, Any]:
    """Extracción multi-fuente + descarga de texto completo (si está activa)."""
    scrapes = registry.run_all(db)
    full_n = 0
    if FETCH_FULL_TEXT:
        try:
            full_n = full_text.descargar_pendientes(db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Texto completo falló: %s", exc)
    return {
        "fuentes": [asdict(s) for s in scrapes],
        "texto_completo_descargado": full_n,
    }


def _resolver(db, pub_id: str) -> P | None:
    """Busca una publicación por url_origen o por UUID (sin romper con ids inválidos)."""
    p = db.scalar(select(P).where(P.url_origen == pub_id))
    if p:
        return p
    try:
        uuidlib.UUID(str(pub_id))
    except ValueError:
        return None  # no es UUID ni url_origen conocida → no existe
    return db.get(P, pub_id)


def _serializar(p: P) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "fuente": p.fuente,
        "titulo": p.titulo,
        "fecha_publicacion": p.fecha_publicacion.isoformat()
        if p.fecha_publicacion
        else None,
        "tipo_edicion": p.tipo_edicion,
        "tipo_documento": p.tipo_documento,
        "sector": p.sector,
        "nivel_relevancia": p.nivel_relevancia,
        "resumen_ia": p.resumen_ia,
        "entidades": p.entidades,
        "palabras_clave": p.palabras_clave,
        # Inteligencia enfocada a Xignux.
        "autoridad_emisora": p.autoridad_emisora,
        "empresas_afectadas": p.empresas_afectadas,
        "productos_afectados": p.productos_afectados,
        "plantas_afectadas": p.plantas_afectadas,
        "nivel_riesgo": p.nivel_riesgo,
        "horizonte_impacto": p.horizonte_impacto,
        "por_que_importa": p.por_que_importa,
        "impacto_potencial": p.impacto_potencial,
        "accion_recomendada": p.accion_recomendada,
        "area_responsable": p.area_responsable,
        "procesado_por_ia": p.procesado_por_ia,
        "revisado": p.revisado,
        "descartado": p.descartado,
        "url_origen": p.url_origen,
        "url_pdf": p.url_pdf,
        "creado_en": p.creado_en.isoformat() if p.creado_en else None,
    }


# --------------------------------------------------------------------------- #
#  Lectura                                                                     #
# --------------------------------------------------------------------------- #
@app.get("/api/stats")
def stats() -> dict[str, Any]:
    """Conteos agregados para el dashboard."""
    db = get_session()
    try:
        total = db.scalar(select(func.count()).select_from(P)) or 0
        procesadas = (
            db.scalar(
                select(func.count()).select_from(P).where(P.procesado_por_ia.is_(True))
            )
            or 0
        )

        def _group(col):
            return {
                k or "—": v
                for k, v in db.execute(
                    select(col, func.count()).group_by(col).order_by(func.count().desc())
                )
            }

        return {
            "total": total,
            "procesadas": procesadas,
            "pendientes": total - procesadas,
            "por_fuente": _group(P.fuente),
            "por_sector": _group(P.sector),
            "por_relevancia": _group(P.nivel_relevancia),
            "por_riesgo": _group(P.nivel_riesgo),
            "pipeline_diario": scheduler.estado(),
        }
    finally:
        db.close()


# Prioridad de los niveles de riesgo para el Radar Legislativo.
_ORDEN_RIESGO = ["Crítico", "Alto", "Medio", "Bajo", "Solo monitoreo"]


@app.get("/api/radar")
def radar() -> dict[str, Any]:
    """Radar Legislativo: top alertas de riesgo y conteos para Xignux."""
    db = get_session()
    try:
        base = select(P).where(
            P.descartado.is_(False), P.procesado_por_ia.is_(True)
        )

        # Conteo por nivel de riesgo (en el orden de prioridad definido).
        conteos = {
            k or "—": v
            for k, v in db.execute(
                select(P.nivel_riesgo, func.count())
                .where(P.descartado.is_(False), P.procesado_por_ia.is_(True))
                .group_by(P.nivel_riesgo)
            )
        }
        por_riesgo = {n: conteos.get(n, 0) for n in _ORDEN_RIESGO}

        # Top alertas críticas/altas, más recientes primero.
        criticas = db.scalars(
            base.where(P.nivel_riesgo.in_(["Crítico", "Alto"]))
            .order_by(P.fecha_publicacion.desc(), P.creado_en.desc())
            .limit(10)
        )
        # Empresas de Xignux con más asuntos de riesgo (Crítico/Alto/Medio).
        return {
            "por_riesgo": por_riesgo,
            "criticas": [_serializar(p) for p in criticas],
        }
    finally:
        db.close()


@app.get("/api/empresas")
def empresas() -> dict[str, Any]:
    """Empresas de Xignux dentro del alcance (para filtros del dashboard)."""
    db = get_session()
    try:
        filas = db.scalars(
            select(EmpresaXignux)
            .where(EmpresaXignux.activo.is_(True), EmpresaXignux.en_alcance.is_(True))
            .order_by(EmpresaXignux.id)
        )
        return {
            "items": [
                {"nombre": e.nombre, "unidad_negocio": e.unidad_negocio}
                for e in filas
            ]
        }
    finally:
        db.close()


@app.get("/api/fuentes")
def fuentes() -> dict[str, Any]:
    """Catálogo de ramas de monitoreo con su estado y conteo actual."""
    db = get_session()
    try:
        conteos = {
            k: v
            for k, v in db.execute(
                select(P.fuente, func.count()).group_by(P.fuente)
            )
        }
    finally:
        db.close()

    grupos = []
    for categoria, fuentes_cat in por_categoria().items():
        grupos.append(
            {
                "categoria": categoria,
                "fuentes": [
                    {
                        "clave": f.clave,
                        "nombre": f.nombre,
                        "estado": f.estado,
                        "nota": f.nota,
                        "publicaciones": (
                            sum(conteos.get(n, 0) for n in NOMBRES_CONGRESOS)
                            if f.clave == "CONGRESOS"
                            else conteos.get(f.fuente_db, 0)
                        ),
                    }
                    for f in fuentes_cat
                ],
            }
        )
    return {"grupos": grupos}


@app.get("/api/publicaciones")
def publicaciones(
    fuente: str | None = None,
    sector: str | None = None,
    nivel: str | None = None,
    riesgo: str | None = None,
    empresa: str | None = None,
    q: str | None = None,
    incluir_descartadas: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Lista de publicaciones con filtros opcionales."""
    db = get_session()
    try:
        consulta = select(P)
        if fuente:
            consulta = consulta.where(P.fuente == fuente)
        if sector:
            consulta = consulta.where(P.sector == sector)
        if nivel:
            consulta = consulta.where(P.nivel_relevancia == nivel)
        if riesgo:
            consulta = consulta.where(P.nivel_riesgo == riesgo)
        if empresa:
            # empresas_afectadas es JSONB array -> contención (@>).
            consulta = consulta.where(P.empresas_afectadas.contains([empresa]))
        if not incluir_descartadas:
            consulta = consulta.where(P.descartado.is_(False))
        if q:
            patron = f"%{q}%"
            consulta = consulta.where(
                P.titulo.ilike(patron) | P.resumen_ia.ilike(patron)
            )

        total = db.scalar(
            select(func.count()).select_from(consulta.subquery())
        ) or 0
        filas = db.scalars(
            consulta.order_by(P.fecha_publicacion.desc(), P.creado_en.desc())
            .limit(limit)
            .offset(offset)
        )
        return {"total": total, "items": [_serializar(p) for p in filas]}
    finally:
        db.close()


@app.get("/api/publicaciones/{pub_id}")
def publicacion(pub_id: str) -> dict[str, Any]:
    """Detalle de una publicación (incluye texto completo)."""
    db = get_session()
    try:
        p = _resolver(db, pub_id)
        if not p:
            raise HTTPException(status_code=404, detail="Publicación no encontrada.")
        data = _serializar(p)
        data["texto_completo"] = p.texto_completo
        data["texto_limpio"] = p.texto_limpio
        data["analisis_ia"] = p.analisis_ia
        return data
    finally:
        db.close()


# --------------------------------------------------------------------------- #
#  Acciones (requieren X-API-Key si API_KEY está configurada)                 #
# --------------------------------------------------------------------------- #
class PublicacionUpdate(BaseModel):
    """Campos editables de una publicación desde el frontend."""

    revisado: bool | None = None
    descartado: bool | None = None


@app.post("/api/acciones/scrape", dependencies=[Depends(require_api_key)])
def accion_scrape(background: BackgroundTasks) -> dict[str, Any]:
    """Dispara la extracción multi-fuente en segundo plano."""
    _lanzar_job("scrape", _job_scrape, background)
    return {"trabajo": "scrape", "estado": "running"}


def _job_ia(limite: int | None, reprocesar: bool):
    """Devuelve la función del job de IA (opcionalmente re-analiza todo)."""

    def _run(db) -> dict[str, Any]:
        reiniciadas = 0
        if reprocesar:
            # Marca como pendientes todas las no descartadas para re-analizarlas
            # con el prompt enfocado a Xignux.
            res = db.execute(
                update(P)
                .where(P.descartado.is_(False))
                .values(procesado_por_ia=False)
            )
            reiniciadas = res.rowcount or 0
            db.commit()
            logger.info("Re-análisis: %d publicaciones marcadas como pendientes.", reiniciadas)
        salida = asdict(analyzer.procesar_pendientes(db, limite=limite))
        salida["reiniciadas"] = reiniciadas
        return salida

    return _run


@app.post("/api/acciones/procesar-ia", dependencies=[Depends(require_api_key)])
def accion_procesar_ia(
    background: BackgroundTasks,
    limite: int | None = Query(
        default=None,
        description="Máx. publicaciones a analizar (None=AI_BATCH_LIMIT, 0=todas).",
    ),
    reprocesar: bool = Query(
        default=False,
        description="Si True, reinicia y re-analiza TODAS las publicaciones no "
        "descartadas (usa limite=0 para procesarlas todas).",
    ),
) -> dict[str, Any]:
    """Dispara el análisis por IA de las publicaciones pendientes."""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="DEEPSEEK_API_KEY no está configurada; el análisis por IA "
            "está deshabilitado.",
        )
    # Al reprocesar conviene procesarlas todas salvo que se pida un límite explícito.
    if reprocesar and limite is None:
        limite = 0
    _lanzar_job("ia", _job_ia(limite, reprocesar), background)
    return {"trabajo": "ia", "estado": "running", "reprocesar": reprocesar}


@app.get("/api/acciones/estado")
def acciones_estado() -> dict[str, Any]:
    """Estado actual de los trabajos en segundo plano (para hacer polling)."""
    with _jobs_lock:
        return {k: dict(v) for k, v in _jobs.items()}


@app.patch("/api/publicaciones/{pub_id}", dependencies=[Depends(require_api_key)])
def actualizar_publicacion(pub_id: str, payload: PublicacionUpdate) -> dict[str, Any]:
    """Marca una publicación como revisada y/o descartada."""
    db = get_session()
    try:
        p = _resolver(db, pub_id)
        if not p:
            raise HTTPException(status_code=404, detail="Publicación no encontrada.")
        if payload.revisado is not None:
            p.revisado = payload.revisado
        if payload.descartado is not None:
            p.descartado = payload.descartado
        db.commit()
        return _serializar(p)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return _DASHBOARD_HTML


_DASHBOARD_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>StrateX · Monitoreo Regulatorio</title>
<style>
  :root { --bg:#0f1419; --card:#1a2129; --line:#2a3441; --txt:#e6edf3;
          --muted:#8b98a5; --alta:#f85149; --media:#d29922; --baja:#3fb950;
          --accent:#388bfd; }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--txt); }
  header { padding:20px 24px; border-bottom:1px solid var(--line);
           display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  header h1 { font-size:20px; margin:0; }
  header span { color:var(--muted); font-size:13px; }
  .spacer { flex:1; }
  .wrap { padding:24px; max-width:1200px; margin:0 auto; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
           gap:12px; margin-bottom:20px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; }
  .card .n { font-size:26px; font-weight:700; }
  .card .l { color:var(--muted); font-size:12px; text-transform:uppercase;
             letter-spacing:.5px; }
  .filters { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
  select,input { background:var(--card); color:var(--txt); border:1px solid var(--line);
                 border-radius:8px; padding:8px 10px; font-size:13px; }
  input.q { flex:1; min-width:180px; }
  button { background:var(--accent); color:#fff; border:0; border-radius:8px;
           padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; }
  button.ghost { background:var(--card); border:1px solid var(--line); color:var(--txt); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  #job { font-size:12px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; }
  th,td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--line);
          vertical-align:top; }
  th { color:var(--muted); font-size:12px; text-transform:uppercase; }
  tr:hover td { background:#161d25; }
  .pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px;
          font-weight:600; }
  .Alta { background:rgba(248,81,73,.15); color:var(--alta); }
  .Media { background:rgba(210,153,34,.15); color:var(--media); }
  .Baja { background:rgba(63,185,80,.15); color:var(--baja); }
  .r-critico { background:rgba(248,81,73,.22); color:#ff7b72; }
  .r-alto { background:rgba(248,81,73,.15); color:var(--alta); }
  .r-medio { background:rgba(210,153,34,.15); color:var(--media); }
  .r-bajo { background:rgba(63,185,80,.15); color:var(--baja); }
  .r-monitoreo { background:rgba(139,152,165,.15); color:var(--muted); }
  .tag { display:inline-block; padding:1px 8px; border-radius:6px; font-size:11px;
         background:rgba(56,139,253,.12); color:var(--accent); margin:2px 4px 0 0; }
  /* Radar Legislativo */
  .radar { display:grid; grid-template-columns:repeat(5,1fr); gap:8px;
           margin-bottom:14px; }
  .rk { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:12px 14px; text-align:center; }
  .rk .n { font-size:24px; font-weight:700; }
  .rk .l { font-size:11px; text-transform:uppercase; letter-spacing:.4px;
           color:var(--muted); margin-top:2px; }
  .rk.sel { outline:2px solid var(--accent); }
  .alerta { background:var(--card); border:1px solid var(--line);
            border-left:3px solid var(--alta); border-radius:8px; padding:10px 12px;
            margin-bottom:8px; }
  .alerta .at { font-weight:600; font-size:13px; }
  .alerta .am { color:var(--muted); font-size:12px; margin-top:3px; }
  /* Panel de detalle Xignux */
  .detail { background:#11171f; border:1px solid var(--line); border-radius:8px;
            padding:12px 14px; margin-top:8px; display:grid;
            grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px 18px; }
  .detail .dl { font-size:10.5px; text-transform:uppercase; letter-spacing:.4px;
                color:var(--muted); }
  .detail .dv { font-size:13px; margin-top:2px; }
  .clic { cursor:pointer; }
  .src { color:var(--accent); font-weight:600; font-size:12px; }
  .titulo { font-weight:500; }
  h2.sec { font-size:13px; text-transform:uppercase; letter-spacing:.06em;
           color:var(--muted); margin:28px 0 12px; }
  .cov-cat { margin-bottom:14px; }
  .cov-cat .cn { font-size:12px; color:var(--accent); font-weight:700; margin-bottom:6px; }
  .cov { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:8px; }
  .fsrc { background:var(--card); border:1px solid var(--line); border-radius:8px;
          padding:10px 12px; display:flex; flex-direction:column; gap:4px; }
  .fsrc .fn { font-size:13px; font-weight:600; }
  .fsrc .fnote { font-size:11px; color:var(--muted); line-height:1.4; }
  .est { align-self:flex-start; font-size:10.5px; font-weight:700; padding:1px 8px;
         border-radius:999px; letter-spacing:.03em; }
  .est.ACTIVA { background:rgba(63,185,80,.15); color:var(--baja); }
  .est.PENDIENTE { background:rgba(210,153,34,.15); color:var(--media); }
  .est.BLOQUEADA { background:rgba(248,81,73,.15); color:var(--alta); }
  .est .c { font-variant-numeric:tabular-nums; opacity:.8; }
  .resumen { color:var(--muted); font-size:12.5px; margin-top:3px; }
  .rowact { display:flex; gap:6px; margin-top:6px; }
  .rowact button { padding:3px 8px; font-size:11px; font-weight:600; }
  a { color:var(--accent); text-decoration:none; }
  .muted { color:var(--muted); }
</style>
</head>
<body>
<header>
  <h1>📑 StrateX</h1><span>Monitoreo Regulatorio Automatizado · México</span>
  <div class="spacer"></div>
  <div class="actions">
    <span id="job"></span>
    <button id="btn-scrape" class="ghost">🔄 Buscar nuevas</button>
    <button id="btn-ia" class="ghost">🤖 Analizar pendientes</button>
    <button id="btn-reia" class="ghost" title="Reinicia y re-analiza TODO con el enfoque Xignux">♻️ Re-analizar todo</button>
    <button id="btn-key" class="ghost" title="Configurar API key">🔑</button>
  </div>
</header>
<div class="wrap">
  <div class="cards" id="cards"></div>
  <p class="muted" id="daily" style="margin:-8px 0 16px"></p>

  <h2 class="sec">📡 Radar Legislativo · riesgo para Xignux</h2>
  <div class="radar" id="radar"></div>
  <div id="alertas"></div>

  <h2 class="sec">Cobertura regulatoria · ramas de monitoreo</h2>
  <div id="cobertura"></div>
  <h2 class="sec">Publicaciones</h2>
  <div class="filters">
    <select id="f-fuente"><option value="">Todas las fuentes</option></select>
    <select id="f-sector"><option value="">Todos los sectores</option></select>
    <select id="f-empresa"><option value="">Todas las empresas</option></select>
    <select id="f-nivel">
      <option value="">Toda relevancia</option>
      <option>Alta</option><option>Media</option><option>Baja</option>
    </select>
    <select id="f-riesgo">
      <option value="">Todo riesgo</option>
      <option>Crítico</option><option>Alto</option><option>Medio</option>
      <option>Bajo</option><option>Solo monitoreo</option>
    </select>
    <input id="f-q" class="q" placeholder="Buscar en título o resumen…">
  </div>
  <table>
    <thead><tr><th>Fecha</th><th>Fuente</th><th>Riesgo</th><th>Empresa(s)</th>
      <th>Publicación</th></tr></thead>
    <tbody id="rows"><tr><td colspan="5" class="muted">Cargando…</td></tr></tbody>
  </table>
  <p class="muted" id="count" style="margin-top:14px"></p>
</div>
<script>
const $ = s => document.querySelector(s);
const KEY = () => localStorage.getItem('stratex_api_key') || '';
const headers = () => KEY() ? {'X-API-Key': KEY(), 'Content-Type':'application/json'}
                            : {'Content-Type':'application/json'};
const esc = s => (s==null?'':String(s)).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const RKMAP = {'Crítico':'r-critico','Alto':'r-alto','Medio':'r-medio','Bajo':'r-bajo','Solo monitoreo':'r-monitoreo'};
const rkClass = r => RKMAP[r] || 'r-monitoreo';
const RIESGOS = ['Crítico','Alto','Medio','Bajo','Solo monitoreo'];

async function loadStats() {
  const s = await (await fetch('/api/stats')).json();
  $('#cards').innerHTML = [
    ['Total', s.total], ['Analizadas', s.procesadas], ['Pendientes', s.pendientes],
    ['Riesgo Crítico', (s.por_riesgo||{})['Crítico']||0],
  ].map(([l,n]) => `<div class="card"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');
  const fill = (sel, obj) => { sel.length = 1; for (const k in obj)
    if (k!=='—') sel.innerHTML += `<option>${esc(k)}</option>`; };
  fill($('#f-fuente'), s.por_fuente); fill($('#f-sector'), s.por_sector);
  const pd = s.pipeline_diario || {};
  $('#daily').textContent = pd.activo
    ? `⏱️ Análisis automático diario activado (${pd.hora_utc}:00 UTC). Próxima corrida: ${pd.proxima_corrida_utc} UTC.`
    : '⏸️ Análisis automático diario desactivado.';
}
async function loadEmpresas() {
  try {
    const d = await (await fetch('/api/empresas')).json();
    const sel = $('#f-empresa'); sel.length = 1;
    d.items.forEach(e => sel.innerHTML += `<option>${esc(e.nombre)}</option>`);
  } catch (_) {}
}
async function loadRadar() {
  const d = await (await fetch('/api/radar')).json();
  const pr = d.por_riesgo || {};
  $('#radar').innerHTML = RIESGOS.map(r => `
    <div class="rk clic ${$('#f-riesgo').value===r?'sel':''}" onclick="filtrarRiesgo('${r}')">
      <div class="n">${pr[r]||0}</div>
      <div class="l"><span class="pill ${rkClass(r)}">${r}</span></div>
    </div>`).join('');
  const a = d.criticas || [];
  $('#alertas').innerHTML = a.length ? a.map(r => `
    <div class="alerta">
      <div class="at"><span class="pill ${rkClass(r.nivel_riesgo)}">${r.nivel_riesgo||''}</span>
        <a href="${esc(r.url_origen)}" target="_blank">${esc(r.titulo)}</a></div>
      <div class="am">${esc(r.fuente)}${r.fecha_publicacion?(' · '+r.fecha_publicacion):''}
        ${(r.empresas_afectadas||[]).map(e=>'· '+esc(e)).join(' ')}</div>
      ${r.por_que_importa?`<div class="am">▸ ${esc(r.por_que_importa)}</div>`:''}
      ${r.accion_recomendada?`<div class="am">✅ ${esc(r.accion_recomendada)}</div>`:''}
    </div>`).join('') : '<p class="muted">Sin alertas críticas o altas por ahora.</p>';
}
function filtrarRiesgo(r) {
  $('#f-riesgo').value = ($('#f-riesgo').value===r) ? '' : r;
  loadRadar(); loadRows();
}
async function loadCobertura() {
  const d = await (await fetch('/api/fuentes')).json();
  $('#cobertura').innerHTML = d.grupos.map(g => `
    <div class="cov-cat"><div class="cn">${g.categoria}</div>
      <div class="cov">${g.fuentes.map(f => `
        <div class="fsrc">
          <span class="est ${f.estado}">${f.estado}${f.publicaciones?(' · <span class="c">'+f.publicaciones+'</span>'):''}</span>
          <div class="fn">${f.nombre}</div>
          <div class="fnote">${f.nota}</div>
        </div>`).join('')}</div>
    </div>`).join('');
}
function detalleXignux(r) {
  const campo = (l, v) => v ? `<div><div class="dl">${l}</div><div class="dv">${esc(v)}</div></div>` : '';
  const lista = (l, arr) => (arr && arr.length)
    ? `<div><div class="dl">${l}</div><div class="dv">${arr.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</div></div>` : '';
  const cuerpo = [
    campo('Autoridad emisora', r.autoridad_emisora),
    campo('Tipo de documento', r.tipo_documento),
    campo('Sector', r.sector),
    lista('Empresas afectadas', r.empresas_afectadas),
    lista('Productos afectados', r.productos_afectados),
    lista('Plantas afectadas', r.plantas_afectadas),
    campo('Horizonte de impacto', r.horizonte_impacto),
    campo('Área responsable', r.area_responsable),
    campo('¿Por qué le importa a Xignux?', r.por_que_importa),
    campo('Impacto potencial', r.impacto_potencial),
    campo('Acción recomendada', r.accion_recomendada),
    lista('Palabras clave', r.palabras_clave),
  ].join('');
  return cuerpo ? `<div class="detail">${cuerpo}</div>` : '';
}
async function loadRows() {
  const p = new URLSearchParams();
  if ($('#f-fuente').value) p.set('fuente', $('#f-fuente').value);
  if ($('#f-sector').value) p.set('sector', $('#f-sector').value);
  if ($('#f-empresa').value) p.set('empresa', $('#f-empresa').value);
  if ($('#f-nivel').value) p.set('nivel', $('#f-nivel').value);
  if ($('#f-riesgo').value) p.set('riesgo', $('#f-riesgo').value);
  if ($('#f-q').value) p.set('q', $('#f-q').value);
  const d = await (await fetch('/api/publicaciones?'+p)).json();
  $('#count').textContent = `${d.items.length} de ${d.total} publicaciones`;
  $('#rows').innerHTML = d.items.map(r => `
    <tr>
      <td class="muted">${r.fecha_publicacion||''}</td>
      <td><span class="src">${esc(r.fuente)}</span></td>
      <td>${r.nivel_riesgo?`<span class="pill ${rkClass(r.nivel_riesgo)}">${r.nivel_riesgo}</span>`:'<span class="muted">—</span>'}</td>
      <td>${(r.empresas_afectadas||[]).map(e=>`<span class="tag">${esc(e)}</span>`).join('')||'<span class="muted">—</span>'}</td>
      <td><div class="titulo clic" onclick="toggleDet('${r.id}')">▸ <a href="${esc(r.url_origen)}" target="_blank" onclick="event.stopPropagation()">${esc(r.titulo)}</a></div>
          <div class="resumen">${esc(r.resumen_ia)}</div>
          <div id="det-${r.id}" style="display:none">${detalleXignux(r)}</div>
          <div class="rowact">
            <button class="ghost" onclick="marcar('${r.id}',{revisado:${!r.revisado}})">${r.revisado?'✓ Revisado':'Marcar revisado'}</button>
            <button class="ghost" onclick="marcar('${r.id}',{descartado:true})">Descartar</button>
          </div></td>
    </tr>`).join('') || '<tr><td colspan="5" class="muted">Sin resultados</td></tr>';
}
function toggleDet(id) {
  const el = $('#det-'+id); if (el) el.style.display = el.style.display==='none' ? 'block' : 'none';
}
async function marcar(id, cambios) {
  const resp = await fetch('/api/publicaciones/'+id, {
    method:'PATCH', headers: headers(), body: JSON.stringify(cambios)});
  if (resp.status === 401) return askKey('Se requiere API key para esta acción.');
  loadRows();
}
let pollTimer;
async function pollJobs() {
  const j = await (await fetch('/api/acciones/estado')).json();
  const running = Object.entries(j).filter(([,v]) => v.estado==='running').map(([k]) => k);
  if (running.length) {
    $('#job').textContent = '⏳ ejecutando: ' + running.join(', ');
    if (!pollTimer) pollTimer = setInterval(pollJobs, 3000);
  } else {
    $('#job').textContent = '';
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; loadStats(); loadRadar(); loadRows(); }
  }
}
async function dispara(url, label) {
  const resp = await fetch(url, {method:'POST', headers: headers()});
  if (resp.status === 401) return askKey('Se requiere API key para '+label+'.');
  if (resp.status === 409) { $('#job').textContent = 'Ya hay un trabajo en curso.'; return; }
  if (resp.status === 503) { const e = await resp.json(); alert(e.detail); return; }
  pollJobs();
}
function askKey(msg) {
  const k = prompt((msg? msg+'\\n\\n':'')+'Pega tu API key (X-API-Key). Vacío para borrarla:', KEY());
  if (k === null) return;
  if (k) localStorage.setItem('stratex_api_key', k); else localStorage.removeItem('stratex_api_key');
}
$('#btn-scrape').onclick = () => dispara('/api/acciones/scrape', 'buscar nuevas');
$('#btn-ia').onclick = () => dispara('/api/acciones/procesar-ia', 'analizar con IA');
$('#btn-reia').onclick = () => {
  if (confirm('Esto reinicia y re-analiza TODAS las publicaciones con el enfoque Xignux. '
    + 'Consume llamadas a la IA y toma varios minutos. ¿Continuar?'))
    dispara('/api/acciones/procesar-ia?reprocesar=true', 're-analizar todo');
};
$('#btn-key').onclick = () => askKey('');
let t; const deb = () => { clearTimeout(t); t = setTimeout(loadRows, 300); };
['#f-fuente','#f-sector','#f-empresa','#f-nivel'].forEach(s => $(s).onchange = loadRows);
$('#f-riesgo').onchange = () => { loadRadar(); loadRows(); };
$('#f-q').oninput = deb;
loadStats(); loadEmpresas(); loadRadar(); loadCobertura(); loadRows(); pollJobs();
</script>
</body>
</html>"""
