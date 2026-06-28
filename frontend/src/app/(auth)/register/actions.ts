"use server"

import { z } from "zod"

import { api, ApiError } from "@/lib/api"
import { registerSchema } from "@/lib/validations/auth"

const registerResponseSchema = z.object({
  user: z.object({
    id: z.string(),
    nombre: z.string(),
    apellido: z.string(),
    email: z.string(),
    must_change_password: z.boolean(),
  }),
  default_password: z.string(),
})

export type RegisterState = {
  error?: string
  fieldErrors?: { nombre?: string; apellido?: string; email?: string }
  success?: boolean
  defaultPassword?: string
  email?: string
}

export async function registerAction(
  _prev: RegisterState,
  formData: FormData,
): Promise<RegisterState> {
  const parsed = registerSchema.safeParse({
    nombre: formData.get("nombre"),
    apellido: formData.get("apellido"),
    email: formData.get("email"),
  })
  if (!parsed.success) {
    const f = parsed.error.flatten().fieldErrors
    return {
      fieldErrors: { nombre: f.nombre?.[0], apellido: f.apellido?.[0], email: f.email?.[0] },
    }
  }

  try {
    const data = await api("/v1/auth/register", {
      method: "POST",
      json: parsed.data,
      schema: registerResponseSchema,
    })
    return { success: true, defaultPassword: data.default_password, email: data.user.email }
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      return { error: "Ya existe un usuario con ese correo electrónico." }
    }
    return { error: "No se pudo completar el registro. Inténtalo de nuevo." }
  }
}
