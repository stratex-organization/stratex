"use client"

import { useActionState } from "react"
import Link from "next/link"
import { CheckCircle2Icon, Loader2Icon } from "lucide-react"

import { registerAction, type RegisterState } from "@/app/(auth)/register/actions"
import { FieldError, FormError } from "@/components/auth/field-error"
import { Button, buttonVariants } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function RegisterForm() {
  const [state, formAction, isPending] = useActionState<RegisterState, FormData>(registerAction, {})

  if (state.success) {
    return (
      <div className="flex flex-col gap-4">
        <div className="text-foreground flex items-center gap-2">
          <CheckCircle2Icon className="size-5 text-emerald-600 dark:text-emerald-500" />
          <p className="font-medium">Usuario registrado correctamente</p>
        </div>
        <p className="text-muted-foreground text-sm">
          Comparte estas credenciales con <span className="text-foreground">{state.email}</span>.
          Deberá cambiar la contraseña en su primer inicio de sesión.
        </p>
        <div className="bg-muted/40 rounded-lg border p-3 text-sm">
          <div className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground">Contraseña temporal</span>
            <code className="bg-background text-foreground ring-foreground/10 rounded px-2 py-1 font-mono ring-1">
              {state.defaultPassword}
            </code>
          </div>
        </div>
        <Link href="/login" className={buttonVariants({ size: "lg", className: "w-full" })}>
          Ir a iniciar sesión
        </Link>
      </div>
    )
  }

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <FormError message={state.error} />

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="nombre">Nombre</Label>
          <Input
            id="nombre"
            name="nombre"
            autoComplete="given-name"
            placeholder="Andrés"
            aria-invalid={!!state.fieldErrors?.nombre}
            required
          />
          <FieldError message={state.fieldErrors?.nombre} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="apellido">Apellido</Label>
          <Input
            id="apellido"
            name="apellido"
            autoComplete="family-name"
            placeholder="Calderón"
            aria-invalid={!!state.fieldErrors?.apellido}
            required
          />
          <FieldError message={state.fieldErrors?.apellido} />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Correo electrónico</Label>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="tucorreo@stratex.com"
          aria-invalid={!!state.fieldErrors?.email}
          required
        />
        <FieldError message={state.fieldErrors?.email} />
      </div>

      <Button type="submit" size="lg" className="mt-1 w-full" disabled={isPending}>
        {isPending && <Loader2Icon className="animate-spin" />}
        Registrar usuario
      </Button>

      <p className="text-muted-foreground text-center text-sm">
        ¿Ya tienes cuenta?{" "}
        <Link href="/login" className="text-foreground font-medium hover:underline">
          Inicia sesión
        </Link>
      </p>
    </form>
  )
}
