"use server"

import { auth } from "@/auth"
import { api, ApiError } from "@/lib/api"
import { changePasswordSchema } from "@/lib/validations/auth"

export type ChangePasswordState = {
  error?: string
  fieldErrors?: { currentPassword?: string; newPassword?: string; confirmPassword?: string }
  success?: boolean
}

export async function changePasswordAction(
  _prev: ChangePasswordState,
  formData: FormData,
): Promise<ChangePasswordState> {
  const parsed = changePasswordSchema.safeParse({
    currentPassword: formData.get("currentPassword"),
    newPassword: formData.get("newPassword"),
    confirmPassword: formData.get("confirmPassword"),
  })
  if (!parsed.success) {
    const f = parsed.error.flatten().fieldErrors
    return {
      fieldErrors: {
        currentPassword: f.currentPassword?.[0],
        newPassword: f.newPassword?.[0],
        confirmPassword: f.confirmPassword?.[0],
      },
    }
  }

  const session = await auth()
  if (!session?.accessToken) {
    return { error: "Tu sesión expiró. Inicia sesión de nuevo." }
  }

  try {
    await api("/v1/auth/change-password", {
      method: "POST",
      json: {
        current_password: parsed.data.currentPassword,
        new_password: parsed.data.newPassword,
      },
      headers: { Authorization: `Bearer ${session.accessToken}` },
    })
    return { success: true }
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 400) {
        return { error: "La contraseña actual es incorrecta." }
      }
      const detail = (error.body as { detail?: string } | undefined)?.detail
      if (detail) return { error: detail }
    }
    return { error: "No se pudo cambiar la contraseña. Inténtalo de nuevo." }
  }
}
