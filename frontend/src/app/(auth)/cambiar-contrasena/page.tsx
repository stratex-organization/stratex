import type { Metadata } from "next"

import { auth } from "@/auth"
import { ChangePasswordForm } from "@/components/auth/change-password-form"

export const metadata: Metadata = { title: "Cambiar contraseña · Stratex" }

export default async function ChangePasswordPage() {
  const session = await auth()
  const nombre = session?.user?.nombre

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Cambia tu contraseña</h1>
        <p className="text-muted-foreground text-sm">
          {nombre ? `Hola ${nombre}. ` : ""}
          Por seguridad, debes definir una nueva contraseña antes de continuar.
        </p>
      </div>
      <ChangePasswordForm />
    </div>
  )
}
