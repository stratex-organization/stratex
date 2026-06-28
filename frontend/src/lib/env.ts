import { z } from "zod"

/**
 * Validación de variables de entorno públicas (cliente).
 * Solo variables NEXT_PUBLIC_* — nunca secretos.
 * Falla rápido en build/arranque si falta algo o tiene formato inválido.
 */
const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
})

export const env = clientEnvSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
})
