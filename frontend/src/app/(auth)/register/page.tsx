import type { Metadata } from "next"

import { RegisterForm } from "@/components/auth/register-form"

export const metadata: Metadata = { title: "Registrar usuario · Stratex" }

export default function RegisterPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Registrar usuario</h1>
        <p className="text-muted-foreground text-sm">
          Alta controlada de acceso. Se asignará una contraseña temporal que el usuario deberá
          cambiar en su primer inicio de sesión.
        </p>
      </div>
      <RegisterForm />
    </div>
  )
}
