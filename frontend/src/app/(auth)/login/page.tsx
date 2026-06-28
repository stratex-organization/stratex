import type { Metadata } from "next"

import { LoginForm } from "@/components/auth/login-form"

export const metadata: Metadata = { title: "Iniciar sesión · Stratex" }

export default function LoginPage() {
  return (
    <div>
      <h1 className="text-foreground text-[28px] font-bold tracking-tight">Iniciar sesión</h1>
      <p className="text-muted-foreground mt-2 text-[14.5px]">
        Ingresa tus credenciales para acceder a Stratex.
      </p>
      <div className="mt-[30px]">
        <LoginForm />
      </div>
    </div>
  )
}
