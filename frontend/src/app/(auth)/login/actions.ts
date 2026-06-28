"use server"

import { AuthError } from "next-auth"

import { signIn } from "@/auth"
import { loginSchema } from "@/lib/validations/auth"

export type LoginState = {
  error?: string
  fieldErrors?: { email?: string; password?: string }
}

export async function loginAction(_prev: LoginState, formData: FormData): Promise<LoginState> {
  const parsed = loginSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
  })
  if (!parsed.success) {
    const f = parsed.error.flatten().fieldErrors
    return { fieldErrors: { email: f.email?.[0], password: f.password?.[0] } }
  }

  try {
    // El middleware redirige a /cambiar-contrasena si el usuario debe cambiar su contraseña.
    await signIn("credentials", {
      email: parsed.data.email,
      password: parsed.data.password,
      redirectTo: "/home",
    })
  } catch (error) {
    if (error instanceof AuthError) {
      return { error: "Correo o contraseña incorrectos." }
    }
    // signIn lanza un redirect en éxito: debe propagarse.
    throw error
  }
  return {}
}
