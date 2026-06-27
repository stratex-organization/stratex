"""Catálogo de los 32 congresos estatales de México.

Cada entrada es (clave_estado, nombre, url_base). Las URLs son el sitio del
poder legislativo de cada entidad. Son sitios heterogéneos: este catálogo los
hace de primera clase en el sistema; la extracción se hace con el scraper
genérico (y ScrapingBee cuando el sitio bloquea IP extranjera).
"""

from __future__ import annotations

CONGRESOS: list[tuple[str, str, str]] = [
    ("AGS", "Congreso de Aguascalientes", "https://congresoags.gob.mx/"),
    ("BC", "Congreso de Baja California", "https://www.congresobc.gob.mx/"),
    ("BCS", "Congreso de Baja California Sur", "https://www.cbcs.gob.mx/"),
    ("CAMP", "Congreso de Campeche", "https://congresocam.gob.mx/"),
    ("CHIS", "Congreso de Chiapas", "https://www.congresochiapas.gob.mx/"),
    ("CHIH", "Congreso de Chihuahua", "https://www.congresochihuahua.gob.mx/"),
    ("CDMX", "Congreso de la Ciudad de México", "https://www.congresocdmx.gob.mx/"),
    ("COAH", "Congreso de Coahuila", "https://www.congresocoahuila.gob.mx/"),
    ("COL", "Congreso de Colima", "https://www.congresocol.gob.mx/"),
    ("DGO", "Congreso de Durango", "https://congresodurango.gob.mx/"),
    ("GTO", "Congreso de Guanajuato", "https://www.congresogto.gob.mx/"),
    ("GRO", "Congreso de Guerrero", "https://congresogro.gob.mx/inicio/"),
    ("HGO", "Congreso de Hidalgo", "https://www.congreso-hidalgo.gob.mx/"),
    ("JAL", "Congreso de Jalisco", "https://www.congresojal.gob.mx/"),
    ("MEX", "Congreso del Estado de México", "https://www.legislativoedomex.gob.mx/"),
    ("MICH", "Congreso de Michoacán", "https://congresomich.site/"),
    ("MOR", "Congreso de Morelos", "https://congresomorelos.gob.mx/"),
    ("NAY", "Congreso de Nayarit", "https://congresonayarit.gob.mx/"),
    ("NL", "Congreso de Nuevo León", "https://www.hcnl.gob.mx/"),
    ("OAX", "Congreso de Oaxaca", "https://www.congresooaxaca.gob.mx/"),
    ("PUE", "Congreso de Puebla", "https://congresopuebla.gob.mx/"),
    ("QRO", "Congreso de Querétaro", "https://legislaturaqro.gob.mx/"),
    ("QROO", "Congreso de Quintana Roo", "https://www.congresoqroo.gob.mx/"),
    ("SLP", "Congreso de San Luis Potosí", "https://congresosanluis.gob.mx/"),
    ("SIN", "Congreso de Sinaloa", "https://www.congresosinaloa.gob.mx/"),
    ("SON", "Congreso de Sonora", "https://congresoson.gob.mx/"),
    ("TAB", "Congreso de Tabasco", "https://congresotabasco.gob.mx/"),
    ("TAMS", "Congreso de Tamaulipas", "https://www.congresotamaulipas.gob.mx/"),
    ("TLAX", "Congreso de Tlaxcala", "https://congresodetlaxcala.gob.mx/"),
    ("VER", "Congreso de Veracruz", "https://www.legisver.gob.mx/"),
    ("YUC", "Congreso de Yucatán", "https://www.congresoyucatan.gob.mx/"),
    ("ZAC", "Congreso de Zacatecas", "https://www.congresozac.gob.mx/"),
]
