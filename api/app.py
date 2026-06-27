"""API REST + dashboard de StrateX (FastAPI).

Expone las publicaciones analizadas con filtros por fuente, sector, relevancia
y búsqueda de texto, además de estadísticas agregadas. La raíz ("/") sirve un
dashboard HTML autocontenido que consume estos endpoints.

Ejecutar:
    uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from database import get_session, init_db
from models import PublicacionOficial as P

app = FastAPI(title="StrateX RegTech API", version="1.0")


@app.on_event("startup")
def _startup() -> None:
    # Garantiza que el esquema/columnas existan al levantar la API.
    init_db()


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
        "procesado_por_ia": p.procesado_por_ia,
        "url_origen": p.url_origen,
        "url_pdf": p.url_pdf,
        "creado_en": p.creado_en.isoformat() if p.creado_en else None,
    }


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
        }
    finally:
        db.close()


@app.get("/api/publicaciones")
def publicaciones(
    fuente: str | None = None,
    sector: str | None = None,
    nivel: str | None = None,
    q: str | None = None,
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
        p = db.scalar(select(P).where(P.url_origen == pub_id)) or db.get(P, pub_id)
        if not p:
            return {"error": "no encontrada"}
        data = _serializar(p)
        data["texto_completo"] = p.texto_completo
        data["texto_limpio"] = p.texto_limpio
        data["analisis_ia"] = p.analisis_ia
        return data
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
           display:flex; align-items:baseline; gap:12px; }
  header h1 { font-size:20px; margin:0; }
  header span { color:var(--muted); font-size:13px; }
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
  input { flex:1; min-width:180px; }
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
  .src { color:var(--accent); font-weight:600; font-size:12px; }
  .titulo { font-weight:500; }
  .resumen { color:var(--muted); font-size:12.5px; margin-top:3px; }
  a { color:var(--accent); text-decoration:none; }
  .muted { color:var(--muted); }
</style>
</head>
<body>
<header>
  <h1>📑 StrateX</h1><span>Monitoreo Regulatorio Automatizado · México</span>
</header>
<div class="wrap">
  <div class="cards" id="cards"></div>
  <div class="filters">
    <select id="f-fuente"><option value="">Todas las fuentes</option></select>
    <select id="f-sector"><option value="">Todos los sectores</option></select>
    <select id="f-nivel">
      <option value="">Toda relevancia</option>
      <option>Alta</option><option>Media</option><option>Baja</option>
    </select>
    <input id="f-q" placeholder="Buscar en título o resumen…">
  </div>
  <table>
    <thead><tr><th>Fecha</th><th>Fuente</th><th>Sector</th><th>Rel.</th>
      <th>Publicación</th></tr></thead>
    <tbody id="rows"><tr><td colspan="5" class="muted">Cargando…</td></tr></tbody>
  </table>
  <p class="muted" id="count" style="margin-top:14px"></p>
</div>
<script>
const $ = s => document.querySelector(s);
async function loadStats() {
  const s = await (await fetch('/api/stats')).json();
  $('#cards').innerHTML = [
    ['Total', s.total], ['Analizadas', s.procesadas], ['Pendientes', s.pendientes],
    ['Relevancia Alta', (s.por_relevancia||{})['Alta']||0],
  ].map(([l,n]) => `<div class="card"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');
  const fill = (sel, obj) => { for (const k in obj)
    if (k!=='—') sel.innerHTML += `<option>${k}</option>`; };
  fill($('#f-fuente'), s.por_fuente); fill($('#f-sector'), s.por_sector);
}
async function loadRows() {
  const p = new URLSearchParams();
  if ($('#f-fuente').value) p.set('fuente', $('#f-fuente').value);
  if ($('#f-sector').value) p.set('sector', $('#f-sector').value);
  if ($('#f-nivel').value) p.set('nivel', $('#f-nivel').value);
  if ($('#f-q').value) p.set('q', $('#f-q').value);
  const d = await (await fetch('/api/publicaciones?'+p)).json();
  $('#count').textContent = `${d.items.length} de ${d.total} publicaciones`;
  $('#rows').innerHTML = d.items.map(r => `
    <tr>
      <td class="muted">${r.fecha_publicacion||''}</td>
      <td><span class="src">${r.fuente}</span></td>
      <td>${r.sector||'<span class="muted">—</span>'}</td>
      <td>${r.nivel_relevancia?`<span class="pill ${r.nivel_relevancia}">${r.nivel_relevancia}</span>`:''}</td>
      <td><div class="titulo"><a href="${r.url_origen}" target="_blank">${r.titulo}</a></div>
          <div class="resumen">${r.resumen_ia||''}</div></td>
    </tr>`).join('') || '<tr><td colspan="5" class="muted">Sin resultados</td></tr>';
}
let t; const deb = () => { clearTimeout(t); t = setTimeout(loadRows, 300); };
['#f-fuente','#f-sector','#f-nivel'].forEach(s => $(s).onchange = loadRows);
$('#f-q').oninput = deb;
loadStats(); loadRows();
</script>
</body>
</html>"""
