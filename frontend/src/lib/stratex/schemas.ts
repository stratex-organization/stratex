import { z } from "zod"

/**
 * Esquemas Zod de la API oficial de Stratex (Keneth) — RegTech "Radar Legislativo".
 * Base en producción: https://stratex-api-production.up.railway.app/api
 * El frontend la consume vía el proxy /api/stratex (ver src/app/api/stratex).
 *
 * Las respuestas del OpenAPI son genéricas (additionalProperties), así que estos
 * esquemas se derivan de la forma real verificada en vivo.
 */

/** Niveles posibles devueltos por la API (se mantienen como string por robustez). */
export const NIVEL_RELEVANCIA = ["Alta", "Media", "Baja"] as const
export const NIVEL_RIESGO = ["Crítico", "Alto", "Medio", "Bajo", "Solo monitoreo", "—"] as const

/** Una publicación regulatoria con su análisis por IA. */
export const PublicacionSchema = z.object({
  id: z.string(),
  fuente: z.string(),
  titulo: z.string(),
  fecha_publicacion: z.string().nullable().optional(),
  tipo_edicion: z.string().nullable().optional(),
  tipo_documento: z.string().nullable().optional(),
  sector: z.string().nullable().optional(),
  nivel_relevancia: z.string().nullable().optional(),
  resumen_ia: z.string().nullable().optional(),
  entidades: z.array(z.string()).default([]),
  palabras_clave: z.array(z.string()).default([]),
  autoridad_emisora: z.string().nullable().optional(),
  empresas_afectadas: z.array(z.string()).default([]),
  productos_afectados: z.array(z.string()).default([]),
  plantas_afectadas: z.array(z.string()).default([]),
  nivel_riesgo: z.string().nullable().optional(),
  horizonte_impacto: z.string().nullable().optional(),
  por_que_importa: z.string().nullable().optional(),
  impacto_potencial: z.string().nullable().optional(),
  accion_recomendada: z.string().nullable().optional(),
  area_responsable: z.string().nullable().optional(),
  procesado_por_ia: z.boolean().default(false),
  revisado: z.boolean().default(false),
  descartado: z.boolean().default(false),
  url_origen: z.string().nullable().optional(),
  url_pdf: z.string().nullable().optional(),
  creado_en: z.string().nullable().optional(),
  // El detalle puede incluir el texto completo; lo aceptamos opcionalmente.
  texto_completo: z.string().nullable().optional(),
})
export type Publicacion = z.infer<typeof PublicacionSchema>

/** GET /api/publicaciones */
export const PublicacionesResponseSchema = z.object({
  total: z.number(),
  items: z.array(PublicacionSchema),
})
export type PublicacionesResponse = z.infer<typeof PublicacionesResponseSchema>

/** Diccionario etiqueta→conteo (por_fuente, por_sector, etc.). */
const ConteoSchema = z.record(z.string(), z.number())

/** GET /api/stats */
export const StatsSchema = z.object({
  total: z.number(),
  procesadas: z.number(),
  pendientes: z.number(),
  por_fuente: ConteoSchema.default({}),
  por_sector: ConteoSchema.default({}),
  por_relevancia: ConteoSchema.default({}),
  por_riesgo: ConteoSchema.default({}),
})
export type Stats = z.infer<typeof StatsSchema>

/** GET /api/radar */
export const RadarSchema = z.object({
  por_riesgo: ConteoSchema.default({}),
  criticas: z.array(PublicacionSchema).default([]),
})
export type Radar = z.infer<typeof RadarSchema>

/** GET /api/empresas */
export const EmpresaSchema = z.object({
  nombre: z.string(),
  unidad_negocio: z.string().nullable().optional(),
})
export const EmpresasResponseSchema = z.object({
  items: z.array(EmpresaSchema).default([]),
})
export type Empresa = z.infer<typeof EmpresaSchema>

/** GET /api/fuentes */
export const FuenteSchema = z.object({
  clave: z.string(),
  nombre: z.string(),
  estado: z.string(),
  nota: z.string().nullable().optional(),
  publicaciones: z.number().default(0),
})
export const GrupoFuentesSchema = z.object({
  categoria: z.string(),
  fuentes: z.array(FuenteSchema).default([]),
})
export const FuentesResponseSchema = z.object({
  grupos: z.array(GrupoFuentesSchema).default([]),
})
export type Fuente = z.infer<typeof FuenteSchema>
export type GrupoFuentes = z.infer<typeof GrupoFuentesSchema>

/** GET /api/acciones/estado (para futuro panel admin). */
const JobEstadoSchema = z.object({
  estado: z.string(),
  resultado: z.unknown().nullable().optional(),
  error: z.string().nullable().optional(),
})
export const AccionesEstadoSchema = z.object({
  scrape: JobEstadoSchema,
  ia: JobEstadoSchema,
})
export type AccionesEstado = z.infer<typeof AccionesEstadoSchema>
