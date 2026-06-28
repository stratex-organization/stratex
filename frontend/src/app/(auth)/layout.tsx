import type { ReactNode } from "react"
import { LockIcon } from "lucide-react"

import { BrandMark } from "@/components/brand-mark"

const SOURCES = ["DOF", "Congreso de la Unión", "32 congresos locales", "SCJN"]

/** Layout de autenticación: panel de marca (guinda) + área de formulario. */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="bg-background flex min-h-svh lg:h-svh lg:overflow-hidden">
      {/* ===== Panel de marca (solo desktop) ===== */}
      <div
        className="relative hidden flex-[1.15] flex-col justify-between overflow-hidden p-[46px_56px] lg:flex"
        style={{ background: "linear-gradient(155deg,#5E0105 0%,#4A0004 45%,#2E0002 100%)" }}
      >
        {/* textura de puntos */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(rgba(255,255,255,.05) 1px,transparent 1px)",
            backgroundSize: "22px 22px",
          }}
        />
        {/* resplandores naranjas */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-[120px] -right-[100px] size-[420px] rounded-full blur-[20px]"
          style={{ background: "radial-gradient(circle,rgba(255,69,0,.28),transparent 70%)" }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-[160px] -left-[80px] size-[380px] rounded-full blur-[10px]"
          style={{ background: "radial-gradient(circle,rgba(255,69,0,.10),transparent 70%)" }}
        />

        <BrandMark size={42} titleClassName="text-white text-xl" className="relative" />

        {/* copy principal */}
        <div className="relative max-w-[520px]">
          <div
            className="mb-[26px] inline-flex items-center gap-2 rounded-[20px] px-3.5 py-1.5"
            style={{
              background: "rgba(255,255,255,.08)",
              border: "1px solid rgba(255,255,255,.14)",
            }}
          >
            <span
              className="size-[7px] rounded-full"
              style={{ background: "#5ED17E", boxShadow: "0 0 0 3px rgba(94,209,126,.22)" }}
            />
            <span className="text-xs font-semibold tracking-wide" style={{ color: "#F0D9D0" }}>
              Plataforma de inteligencia regulatoria
            </span>
          </div>
          <h1 className="text-[38px] leading-[1.18] font-bold tracking-tight text-balance text-white">
            Monitoreo y extracción de datos{" "}
            <em className="serif" style={{ color: "#FF9166" }}>
              gubernamentales
            </em>{" "}
            de México.
          </h1>
          <p
            className="mt-5 max-w-[440px] text-[15px] leading-relaxed"
            style={{ color: "#E3BFB3" }}
          >
            Acceso controlado a la plataforma. Tus credenciales se transmiten cifradas y protegidas
            de extremo a extremo.
          </p>
          <div className="mt-[30px] flex flex-wrap gap-2.5">
            {SOURCES.map((s) => (
              <span
                key={s}
                className="rounded-[9px] px-[13px] py-2 text-[12.5px] font-semibold"
                style={{
                  color: "#F0D9D0",
                  background: "rgba(255,255,255,.07)",
                  border: "1px solid rgba(255,255,255,.12)",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* footer */}
        <div
          className="relative flex items-center gap-3.5 text-[12.5px] font-medium"
          style={{ color: "#B7837A" }}
        >
          <span>© 2026 Stratex</span>
          <span className="size-1 rounded-full" style={{ background: "#7A4138" }} />
          <span className="flex items-center gap-1.5">
            <LockIcon className="size-3.5" />
            Conexión cifrada
          </span>
        </div>
      </div>

      {/* ===== Área de formulario ===== */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-[388px]">
          <div className="mb-8 flex items-center lg:hidden">
            <BrandMark titleClassName="text-foreground" />
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
