import type { z } from "zod"

import { ApiError } from "@/lib/api"
import {
  AccionesEstadoSchema,
  EmpresasResponseSchema,
  FuentesResponseSchema,
  PublicacionSchema,
  PublicacionesResponseSchema,
  RadarSchema,
  StatsSchema,
} from "./schemas"

/** URL de producción por defecto si no se configura STRATEX_API_URL. */
const DEFAULT_STRATEX_API_URL = "https://stratex-api-production.up.railway.app"

/**
 * Resuelve el origen al que se piden los datos:
 * - En el navegador: el proxy same-origin `/api/stratex` (la URL real y la futura
 *   x-api-key viven solo en el servidor → evita CORS y no expone secretos).
 * - En el servidor: directo a la API oficial (`STRATEX_API_URL`).
 */
function buildUrl(path: string, params?: Record<string, unknown>): string {
  const isServer = typeof window === "undefined"
  const base = isServer
    ? `${(process.env.STRATEX_API_URL ?? DEFAULT_STRATEX_API_URL).replace(/\/$/, "")}/api`
    : "/api/stratex"

  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === "") continue
    qs.set(key, String(value))
  }
  const query = qs.toString()
  return `${base}${path}${query ? `?${query}` : ""}`
}

/** Fetch tipado contra la API oficial (lectura), validado con Zod. */
async function stratexGet<T>(
  path: string,
  schema: z.ZodType<T>,
  params?: Record<string, unknown>,
): Promise<T> {
  const url = buildUrl(path, params)
  const res = await fetch(url, { headers: { Accept: "application/json" } })

  if (!res.ok) {
    const body = await res.json().catch(() => undefined)
    throw new ApiError(res.status, `Stratex API ${res.status} en ${path}`, body)
  }

  const data = await res.json()
  return schema.parse(data)
}

/** Filtros de GET /api/publicaciones. */
export type PublicacionesFilters = {
  fuente?: string
  sector?: string
  nivel?: string
  riesgo?: string
  empresa?: string
  q?: string
  incluir_descartadas?: boolean
  limit?: number
  offset?: number
}

export const stratex = {
  getStats: () => stratexGet("/stats", StatsSchema),
  getRadar: () => stratexGet("/radar", RadarSchema),
  getEmpresas: () => stratexGet("/empresas", EmpresasResponseSchema),
  getFuentes: () => stratexGet("/fuentes", FuentesResponseSchema),
  getPublicaciones: (filters: PublicacionesFilters = {}) =>
    stratexGet("/publicaciones", PublicacionesResponseSchema, filters),
  getPublicacion: (id: string) =>
    stratexGet(`/publicaciones/${encodeURIComponent(id)}`, PublicacionSchema),
  getAccionesEstado: () => stratexGet("/acciones/estado", AccionesEstadoSchema),
}
