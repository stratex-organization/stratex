"use client"

import { useActionState, useState } from "react"
import { ArrowRightIcon, EyeIcon, EyeOffIcon, LockIcon, MailIcon, ShieldIcon } from "lucide-react"

import { loginAction, type LoginState } from "@/app/(auth)/login/actions"
import { FieldError, FormError } from "@/components/auth/field-error"

const fieldClass =
  "h-12 w-full rounded-[11px] border border-input bg-card pl-[42px] text-[14.5px] text-foreground outline-none transition focus:border-primary focus:shadow-[0_0_0_3px_rgba(255,69,0,.13)]"

export function LoginForm() {
  const [state, formAction, isPending] = useActionState<LoginState, FormData>(loginAction, {})
  const [show, setShow] = useState(false)

  return (
    <form action={formAction} className="flex flex-col">
      <FormError message={state.error} />

      {/* Correo */}
      <div>
        <label htmlFor="email" className="text-foreground mb-2 block text-[13px] font-semibold">
          Correo electrónico
        </label>
        <div className="relative flex items-center">
          <MailIcon className="text-muted-faint pointer-events-none absolute left-[14px] size-[18px]" />
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="tucorreo@stratex.com"
            aria-invalid={!!state.fieldErrors?.email}
            required
            className={fieldClass + " pr-[14px]"}
          />
        </div>
        <FieldError message={state.fieldErrors?.email} />
      </div>

      {/* Contraseña */}
      <div className="mt-5">
        <label htmlFor="password" className="text-foreground mb-2 block text-[13px] font-semibold">
          Contraseña
        </label>
        <div className="relative flex items-center">
          <LockIcon className="text-muted-faint pointer-events-none absolute left-[14px] size-[18px]" />
          <input
            id="password"
            name="password"
            type={show ? "text" : "password"}
            autoComplete="current-password"
            placeholder="••••••••"
            aria-invalid={!!state.fieldErrors?.password}
            required
            className={fieldClass + " pr-[46px]"}
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            title="Mostrar u ocultar"
            tabIndex={-1}
            aria-label={show ? "Ocultar contraseña" : "Mostrar contraseña"}
            className="text-muted-faint hover:text-foreground absolute right-2 flex size-[34px] items-center justify-center rounded-md transition-colors"
          >
            {show ? <EyeOffIcon className="size-[18px]" /> : <EyeIcon className="size-[18px]" />}
          </button>
        </div>
        <FieldError message={state.fieldErrors?.password} />
      </div>

      {/* Olvidaste */}
      <div className="mt-3 flex justify-end">
        <a
          href="#"
          className="text-label hover:text-primary text-[13px] font-semibold transition-colors"
        >
          ¿Olvidaste tu contraseña?
        </a>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isPending}
        className="bg-primary text-primary-foreground mt-[22px] flex h-[50px] w-full items-center justify-center gap-2.5 rounded-[11px] text-[15px] font-bold shadow-[0_5px_16px_rgba(255,69,0,.26)] transition hover:bg-[#E63E00] active:translate-y-px disabled:opacity-70"
      >
        {isPending ? "Iniciando…" : "Iniciar sesión"}
        {!isPending && <ArrowRightIcon className="size-[18px]" strokeWidth={2.2} />}
      </button>

      <div className="mt-[26px] flex items-center justify-center gap-2">
        <ShieldIcon className="text-muted-faint size-3.5" />
        <span className="text-muted-faint text-[12.5px] font-medium">
          ¿Necesitas acceso? Contacta a tu administrador.
        </span>
      </div>
    </form>
  )
}
