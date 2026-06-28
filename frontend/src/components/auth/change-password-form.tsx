"use client"

import { useActionState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useSession } from "next-auth/react"
import { Loader2Icon } from "lucide-react"
import { toast } from "sonner"

import {
  changePasswordAction,
  type ChangePasswordState,
} from "@/app/(auth)/cambiar-contrasena/actions"
import { FieldError, FormError } from "@/components/auth/field-error"
import { PasswordInput } from "@/components/auth/password-input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

export function ChangePasswordForm() {
  const [state, formAction, isPending] = useActionState<ChangePasswordState, FormData>(
    changePasswordAction,
    {},
  )
  const router = useRouter()
  const { update } = useSession()
  const handled = useRef(false)

  useEffect(() => {
    if (state.success && !handled.current) {
      handled.current = true
      // Baja la bandera en la sesión (dispara el callback jwt) y entra a la app.
      update({ mustChangePassword: false }).then(() => {
        toast.success("Contraseña actualizada correctamente.")
        router.replace("/")
        router.refresh()
      })
    }
  }, [state.success, update, router])

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <FormError message={state.error} />

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="currentPassword">Contraseña actual</Label>
        <PasswordInput
          id="currentPassword"
          name="currentPassword"
          autoComplete="current-password"
          placeholder="Tu contraseña temporal"
          aria-invalid={!!state.fieldErrors?.currentPassword}
          required
        />
        <FieldError message={state.fieldErrors?.currentPassword} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="newPassword">Nueva contraseña</Label>
        <PasswordInput
          id="newPassword"
          name="newPassword"
          autoComplete="new-password"
          placeholder="Mínimo 8 caracteres, con letras y números"
          aria-invalid={!!state.fieldErrors?.newPassword}
          required
        />
        <FieldError message={state.fieldErrors?.newPassword} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confirmPassword">Confirmar nueva contraseña</Label>
        <PasswordInput
          id="confirmPassword"
          name="confirmPassword"
          autoComplete="new-password"
          placeholder="Repite la nueva contraseña"
          aria-invalid={!!state.fieldErrors?.confirmPassword}
          required
        />
        <FieldError message={state.fieldErrors?.confirmPassword} />
      </div>

      <Button type="submit" size="lg" className="mt-1 w-full" disabled={isPending || state.success}>
        {(isPending || state.success) && <Loader2Icon className="animate-spin" />}
        Cambiar contraseña
      </Button>
    </form>
  )
}
