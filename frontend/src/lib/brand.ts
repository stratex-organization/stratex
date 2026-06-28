/**
 * Colores semánticos de la identidad Xignux usados en datos (sectores, partidos, relevancia,
 * estatus). Son colores guiados por datos: se aplican como estilos en línea sobre badges,
 * avatares, donas y barras. La paleta base de la UI vive en los tokens de `globals.css`.
 */

/** Colores por sector (dona + barras de Regulaciones, KPIs). Usa las etiquetas
 * compuestas que devuelve la API oficial (p. ej. "Administrativo/Gobierno"). */
export const SECTOR_COLORS: Record<string, string> = {
  "Administrativo/Gobierno": "#FF4500",
  "Financiero/Bancario": "#5B7FB0",
  "Fiscal/Tributario": "#D8A450",
  Energía: "#4E9A2A",
  Salud: "#C13B2A",
  "Medio Ambiente": "#2E7D8A",
  Laboral: "#9B2247",
  "Datos Personales/Privacidad": "#7A5BA8",
  Otro: "#8A776F",
}

export function sectorColor(sector: string | null | undefined): string {
  if (!sector) return "#8A776F"
  return SECTOR_COLORS[sector] ?? "#8A776F"
}

/** Estilo de badge por nivel de riesgo (campo `nivel_riesgo` de la API). */
export const RIESGO_BADGE: Record<string, { color: string; bg: string }> = {
  Crítico: { color: "#7A1020", bg: "#FBE0E3" },
  Alto: { color: "#C13B2A", bg: "#FCE9E5" },
  Medio: { color: "#B07A1E", bg: "#FBF1D2" },
  Bajo: { color: "#3C6B1A", bg: "#E9F4DD" },
  "Solo monitoreo": { color: "#5B7FB0", bg: "#E6EEF6" },
  "—": { color: "#7A675F", bg: "#F0EAE6" },
}

export function riesgoBadge(nivel: string | null | undefined): { color: string; bg: string } {
  if (!nivel) return RIESGO_BADGE["—"]
  return RIESGO_BADGE[nivel] ?? RIESGO_BADGE["—"]
}

/** Colores por partido político (avatares y badges en Congreso). */
export const PARTY_COLORS: Record<string, string> = {
  MORENA: "#9B2247",
  PAN: "#0B5FA5",
  PRI: "#C8102E",
  MC: "#F58220",
  PVEM: "#4CA847",
  PT: "#D52B1E",
  PRD: "#E6A800",
}

export function partyColor(party: string): string {
  return PARTY_COLORS[party] ?? "#8A776F"
}

/** Estilo de badge por relevancia / prioridad de cumplimiento. */
export type Relevancia = "Alta" | "Media" | "Baja"

export const RELEVANCIA_BADGE: Record<Relevancia, { color: string; bg: string }> = {
  Alta: { color: "#C13B2A", bg: "#FCE9E5" },
  Media: { color: "#B07A1E", bg: "#FBF1D2" },
  Baja: { color: "#5B7FB0", bg: "#E6EEF6" },
}

/** Iniciales para avatares (máx. 2 letras). */
export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
}
