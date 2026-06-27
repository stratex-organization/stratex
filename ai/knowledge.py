"""Núcleo de conocimiento de Xignux.

Centraliza QUIÉN es Xignux (empresas, productos, marcas, plantas, temas
estratégicos y autoridades) para que la capa de IA enfoque su análisis en el
impacto real para el grupo, en lugar de un análisis regulatorio genérico.

- `seed_knowledge(db)` carga los datos base desde el prompt institucional
  (idempotente: solo inserta si las tablas están vacías).
- `render_contexto(db)` arma un bloque de texto compacto que se inyecta al
  system prompt del analizador.

Las tablas son administrables desde la base de datos: editar/añadir filas en
`empresas_xignux`, `productos_xignux`, etc. cambia el contexto sin tocar código.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import (
    AutoridadRegulatoria,
    EmpresaXignux,
    MarcaXignux,
    ProductoXignux,
    TemaEstrategico,
    UbicacionXignux,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Datos semilla (del prompt institucional de la Plataforma de Inteligencia
# Pública Xignux). Editables luego directamente en la base de datos.
# ---------------------------------------------------------------------------

# nombre, unidad_negocio, descripción, productos, marcas, ubicaciones, temas
_EMPRESAS_SEED: list[dict] = [
    {
        "nombre": "Viakable",
        "unidad_negocio": "Energía / Infraestructura eléctrica",
        "descripcion": (
            "Fabrica y comercializa conductores y cables eléctricos para "
            "infraestructura energética, construcción, industria, utilities y "
            "proyectos de electrificación."
        ),
        "productos": [
            "Cables eléctricos",
            "Conductores de cobre",
            "Conductores de aluminio",
            "Cable de baja tensión",
            "Cable de media tensión",
            "Cable de alta tensión",
            "Cable industrial",
            "Cable para construcción",
            "Cable para infraestructura",
            "Cable para energía",
            "Cable para telecomunicaciones",
        ],
        "marcas": [],
        "ubicaciones": [
            {"nombre": None, "ciudad": None, "estado": "Nuevo León"},
            {
                "nombre": None,
                "ciudad": "San Nicolás de los Garza",
                "estado": "Nuevo León",
            },
            {"nombre": None, "ciudad": None, "estado": "San Luis Potosí"},
        ],
        "temas": [
            "Regulación eléctrica", "CFE", "CRE", "CENACE", "SENER",
            "Transmisión", "Distribución", "Infraestructura eléctrica",
            "Confiabilidad de la red", "Código de Red", "Cobre", "Aluminio",
            "Aranceles", "T-MEC", "Reglas de origen", "Compras públicas",
            "Nearshoring", "Data Centers", "Electromovilidad",
            "Transición energética", "Energías limpias",
            "Costos de electricidad industrial",
        ],
    },
    {
        "nombre": "Qualtia",
        "unidad_negocio": "Alimentos",
        "descripcion": (
            "Produce y comercializa alimentos refrigerados, proteínas, carnes "
            "frías, quesos, alimentos preparados y soluciones para food service."
        ),
        "productos": [
            "Carnes frías", "Jamón", "Salchichas", "Quesos",
            "Productos cárnicos", "Proteínas", "Alimentos refrigerados",
            "Alimentos listos para consumir", "Productos para Food Service",
        ],
        "marcas": [],
        "ubicaciones": [],
        "temas": [
            "COFEPRIS", "NOM-051", "Etiquetado de alimentos", "Sellos frontales",
            "Sodio", "Grasas", "Azúcares", "Alimentos ultraprocesados",
            "Salud pública", "Publicidad de alimentos",
            "Publicidad dirigida a menores", "Inocuidad alimentaria",
            "Trazabilidad", "Cadena fría", "Empaques", "Plásticos",
            "Economía circular", "Agua", "Costos de energía", "Logística",
        ],
    },
    {
        "nombre": "BYDSA",
        "unidad_negocio": "Botanas",
        "descripcion": "Fabrica y comercializa botanas saladas.",
        "productos": [
            "Papas fritas", "Botanas de maíz", "Frituras", "Botanas extruidas",
            "Cacahuates", "Semillas", "Chicharrones", "Totopos", "Pellets",
        ],
        "marcas": ["Leo", "Encanto", "Snaky"],
        "ubicaciones": [
            {"nombre": "Planta Kalos", "ciudad": "Guadalupe", "estado": "Nuevo León"},
            {"nombre": "Planta León", "ciudad": "León", "estado": "Guanajuato"},
        ],
        "temas": [
            "Regulación de botanas", "Etiquetado de alimentos", "NOM-051",
            "IEPS", "Alimentos de alta densidad calórica", "Sodio", "Grasas",
            "Publicidad dirigida a menores", "COFEPRIS", "PROFECO", "Empaques",
            "Plásticos", "Economía circular", "Residuos", "Agua",
            "Costos de energía", "Logística",
        ],
    },
]

# Empresas que NO forman parte del alcance (la IA no debe tratarlas como Xignux).
_EMPRESAS_EXCLUIDAS_SEED: list[dict] = [
    {
        "nombre": "Prolec GE",
        "unidad_negocio": None,
        "descripcion": "Ya no forma parte del alcance relevante de Xignux.",
    },
]

# siglas, nombre, categoría
_AUTORIDADES_SEED: list[tuple[str, str, str]] = [
    ("SENER", "Secretaría de Energía", "Energía"),
    ("CRE", "Comisión Reguladora de Energía", "Energía"),
    ("CFE", "Comisión Federal de Electricidad", "Energía"),
    ("CENACE", "Centro Nacional de Control de Energía", "Energía"),
    ("CONUEE", "Comisión Nacional para el Uso Eficiente de la Energía", "Energía"),
    ("ASEA", "Agencia de Seguridad, Energía y Ambiente", "Energía"),
    ("CNH", "Comisión Nacional de Hidrocarburos", "Energía"),
    ("COFEPRIS", "Comisión Federal para la Protección contra Riesgos Sanitarios",
     "Salud y Alimentos"),
    ("SSA", "Secretaría de Salud", "Salud y Alimentos"),
    ("SENASICA", "Servicio Nacional de Sanidad, Inocuidad y Calidad Agroalimentaria",
     "Salud y Alimentos"),
    ("PROFECO", "Procuraduría Federal del Consumidor", "Salud y Alimentos"),
    ("SEMARNAT", "Secretaría de Medio Ambiente y Recursos Naturales",
     "Medio Ambiente"),
    ("PROFEPA", "Procuraduría Federal de Protección al Ambiente", "Medio Ambiente"),
    ("CONAGUA", "Comisión Nacional del Agua", "Medio Ambiente"),
    ("SE", "Secretaría de Economía", "Economía y Comercio Exterior"),
    ("SAT", "Servicio de Administración Tributaria", "Economía y Comercio Exterior"),
    ("ANAM", "Agencia Nacional de Aduanas de México",
     "Economía y Comercio Exterior"),
    ("SHCP", "Secretaría de Hacienda y Crédito Público",
     "Economía y Comercio Exterior"),
    ("STPS", "Secretaría del Trabajo y Previsión Social", "Laboral"),
    ("IMSS", "Instituto Mexicano del Seguro Social", "Laboral"),
    ("INFONAVIT", "Instituto del Fondo Nacional de la Vivienda para los Trabajadores",
     "Laboral"),
    ("Senado", "Senado de la República", "Legislativo"),
    ("Cámara de Diputados", "Cámara de Diputados", "Legislativo"),
    ("Congresos Locales", "32 Congresos Locales", "Legislativo"),
    ("SCJN", "Suprema Corte de Justicia de la Nación", "Judicial"),
    ("TCC", "Tribunales Colegiados", "Judicial"),
    ("TFJA", "Tribunal Federal de Justicia Administrativa", "Judicial"),
]


def seed_knowledge(db: Session) -> None:
    """Carga el núcleo de conocimiento si las tablas están vacías (idempotente)."""
    _seed_empresas(db)
    _seed_autoridades(db)


def _seed_empresas(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(EmpresaXignux)):
        return
    logger.info("Sembrando núcleo de conocimiento de Xignux (empresas)...")

    for datos in _EMPRESAS_SEED:
        empresa = EmpresaXignux(
            nombre=datos["nombre"],
            unidad_negocio=datos["unidad_negocio"],
            descripcion=datos["descripcion"],
            en_alcance=True,
        )
        db.add(empresa)
        db.flush()  # asigna empresa.id

        for prod in datos["productos"]:
            db.add(ProductoXignux(empresa_id=empresa.id, nombre=prod))
        for marca in datos["marcas"]:
            db.add(MarcaXignux(empresa_id=empresa.id, nombre=marca))
        for ubi in datos["ubicaciones"]:
            db.add(UbicacionXignux(empresa_id=empresa.id, **ubi))
        for tema in datos["temas"]:
            db.add(TemaEstrategico(empresa_id=empresa.id, nombre=tema))

    for datos in _EMPRESAS_EXCLUIDAS_SEED:
        db.add(
            EmpresaXignux(
                nombre=datos["nombre"],
                unidad_negocio=datos["unidad_negocio"],
                descripcion=datos["descripcion"],
                en_alcance=False,
            )
        )

    db.commit()


def _seed_autoridades(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(AutoridadRegulatoria)):
        return
    logger.info("Sembrando catálogo de autoridades regulatorias...")
    for siglas, nombre, categoria in _AUTORIDADES_SEED:
        db.add(
            AutoridadRegulatoria(nombre=nombre, siglas=siglas, categoria=categoria)
        )
    db.commit()


def render_contexto(db: Session) -> str:
    """Arma un bloque de texto con el núcleo de Xignux para el system prompt.

    Devuelve cadena vacía si no hay datos cargados (el analizador opera entonces
    en modo genérico).
    """
    empresas = list(
        db.scalars(
            select(EmpresaXignux)
            .where(EmpresaXignux.activo.is_(True))
            .order_by(EmpresaXignux.id)
        )
    )
    if not empresas:
        return ""

    lineas: list[str] = ["## NÚCLEO DE CONOCIMIENTO — XIGNUX", ""]
    lineas.append(
        "Xignux es un grupo industrial mexicano. Analiza cada documento en "
        "función de su impacto REAL para las siguientes empresas del grupo:"
    )
    lineas.append("")

    excluidas: list[str] = []
    for emp in empresas:
        if not emp.en_alcance:
            excluidas.append(emp.nombre)
            continue

        productos = _nombres(db, ProductoXignux, emp.id)
        marcas = _nombres(db, MarcaXignux, emp.id)
        temas = _nombres(db, TemaEstrategico, emp.id)
        ubicaciones = _render_ubicaciones(db, emp.id)

        lineas.append(f"### {emp.nombre} — {emp.unidad_negocio or 'N/D'}")
        if emp.descripcion:
            lineas.append(emp.descripcion)
        if productos:
            lineas.append(f"- Productos: {', '.join(productos)}")
        if marcas:
            lineas.append(f"- Marcas: {', '.join(marcas)}")
        if ubicaciones:
            lineas.append(f"- Ubicaciones/plantas: {'; '.join(ubicaciones)}")
        if temas:
            lineas.append(f"- Temas estratégicos: {', '.join(temas)}")
        lineas.append("")

    if excluidas:
        lineas.append(
            "IMPORTANTE — Fuera de alcance: NUNCA trates a "
            + ", ".join(excluidas)
            + " como empresa del grupo Xignux, salvo que se solicite "
            "expresamente."
        )
        lineas.append("")

    autoridades = list(
        db.scalars(
            select(AutoridadRegulatoria).order_by(AutoridadRegulatoria.categoria)
        )
    )
    if autoridades:
        lineas.append("### Autoridades relevantes (para identificar la emisora)")
        por_categoria: dict[str, list[str]] = {}
        for aut in autoridades:
            etiqueta = aut.siglas or aut.nombre
            por_categoria.setdefault(aut.categoria or "Otras", []).append(etiqueta)
        for categoria, siglas in por_categoria.items():
            lineas.append(f"- {categoria}: {', '.join(siglas)}")

    return "\n".join(lineas).strip()


def _nombres(db: Session, modelo, empresa_id: int) -> list[str]:
    return list(
        db.scalars(select(modelo.nombre).where(modelo.empresa_id == empresa_id))
    )


def _render_ubicaciones(db: Session, empresa_id: int) -> list[str]:
    filas = list(
        db.scalars(
            select(UbicacionXignux).where(UbicacionXignux.empresa_id == empresa_id)
        )
    )
    salida: list[str] = []
    for u in filas:
        partes = [p for p in (u.nombre, u.ciudad, u.estado) if p]
        if partes:
            salida.append(", ".join(partes))
    return salida
