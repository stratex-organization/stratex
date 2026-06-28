import { z } from "zod"
import { env } from "./env"

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

type ApiOptions<T> = Omit<RequestInit, "body"> & {
  /** Schema Zod para validar y tipar la respuesta JSON. */
  schema?: z.ZodType<T>
  /** Body JSON (se serializa automáticamente). */
  json?: unknown
}

/**
 * Cliente tipado para la API REST de Python (FastAPI).
 * Base: NEXT_PUBLIC_API_URL. Valida la respuesta con Zod cuando se pasa `schema`.
 *
 * Uso:
 *   const items = await api("/v1/sources", { schema: SourcesSchema })
 */
export async function api<T = unknown>(
  path: string,
  { schema, json, headers, ...init }: ApiOptions<T> = {},
): Promise<T> {
  const res = await fetch(`${env.NEXT_PUBLIC_API_URL}${path}`, {
    ...init,
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : undefined,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => undefined)
    throw new ApiError(res.status, `API ${res.status} en ${path}`, body)
  }

  if (res.status === 204) return undefined as T

  const data = await res.json()
  return schema ? schema.parse(data) : (data as T)
}
