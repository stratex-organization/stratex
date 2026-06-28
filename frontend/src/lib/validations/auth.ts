import { z } from "zod"

/** Contraseña por defecto que se asigna al registrar (debe cambiarse en el 1er login). */
export const DEFAULT_PASSWORD = "PonchoCabra123"

export const loginSchema = z.object({
  email: z.string().email("Ingresa un correo electrónico válido."),
  password: z.string().min(1, "Ingresa tu contraseña."),
})

export const registerSchema = z.object({
  nombre: z.string().trim().min(1, "Ingresa el nombre.").max(120),
  apellido: z.string().trim().min(1, "Ingresa el apellido.").max(120),
  email: z.string().email("Ingresa un correo electrónico válido."),
})

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Ingresa tu contraseña actual."),
    newPassword: z
      .string()
      .min(8, "La contraseña debe tener al menos 8 caracteres.")
      .max(128)
      .regex(/[a-zA-Z]/, "Debe incluir al menos una letra.")
      .regex(/[0-9]/, "Debe incluir al menos un número."),
    confirmPassword: z.string().min(1, "Confirma tu nueva contraseña."),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Las contraseñas no coinciden.",
    path: ["confirmPassword"],
  })
  .refine((d) => d.newPassword !== DEFAULT_PASSWORD, {
    message: "La nueva contraseña no puede ser la contraseña por defecto.",
    path: ["newPassword"],
  })
  .refine((d) => d.newPassword !== d.currentPassword, {
    message: "La nueva contraseña debe ser distinta a la actual.",
    path: ["newPassword"],
  })

export type LoginInput = z.infer<typeof loginSchema>
export type RegisterInput = z.infer<typeof registerSchema>
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>
