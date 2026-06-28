"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronRightIcon } from "lucide-react"

import { riesgoBadge } from "@/lib/brand"
import { cn } from "@/lib/utils"
import { stratex } from "@/lib/stratex/client"
import type { Fuente } from "@/lib/stratex/schemas"
import { Skeleton } from "@/components/ui/skeleton"

const sectionLabel = "text-xs font-bold uppercase tracking-[.14em] text-label"
const card = "rounded-[14px] border border-border bg-card"

/** Estilo de badge por estado de la fuente. */
const ESTADO_BADGE: Record<string, { color: string; bg: string; dot: string }> = {
  ACTIVA: { color: "#3C6B1A", bg: "#E9F4DD", dot: "#4E9A2A" },
  PENDIENTE: { color: "#B05A12", bg: "#FBF1D2", dot: "#D8A450" },
  BLOQUEADA: { color: "#C13B2A", bg: "#FCE9E5", dot: "#C13B2A" },
}
function estadoBadge(estado: string) {
  return ESTADO_BADGE[estado] ?? { color: "#7A675F", bg: "#F0EAE6", dot: "#8A776F" }
}

export function CongressView() {
  const [tab, setTab] = useState(0)
  const [fuenteSel, setFuenteSel] = useState<string | null>(null)

  const fuentesQ = useQuery({ queryKey: ["fuentes"], queryFn: stratex.getFuentes })
  const grupos = useMemo(() => fuentesQ.data?.grupos ?? [], [fuentesQ.data])
  const grupoActivo = grupos[tab]

  const pubsQ = useQuery({
    queryKey: ["publicaciones", { fuente: fuenteSel }],
    queryFn: () => stratex.getPublicaciones({ fuente: fuenteSel ?? undefined, limit: 12 }),
    enabled: fuenteSel !== null,
  })

  const totalPubs = useMemo(
    () => grupos.flatMap((g) => g.fuentes).reduce((s, f) => s + f.publicaciones, 0),
    [grupos],
  )

  return (
    <div>
      {/* page header */}
      <div className="mb-5">
        <h1 className="text-foreground text-[25px] font-bold tracking-tight">
          Fuentes de monitoreo
        </h1>
        <p className="text-muted-foreground mt-1.5 text-sm">
          Estado de las{" "}
          <em className="serif">fuentes legislativas, ejecutivas, judiciales y reguladoras</em> que
          alimentan el radar.
        </p>
      </div>

      {/* TABS por categoría */}
      {fuentesQ.isLoading ? (
        <Skeleton className="mb-6 h-10 w-full max-w-2xl" />
      ) : (
        <div className="border-border mb-6 flex flex-wrap items-center gap-1 border-b-[1.5px]">
          {grupos.map((g, i) => {
            const active = i === tab
            const count = g.fuentes.reduce((s, f) => s + f.publicaciones, 0)
            return (
              <button
                key={g.categoria}
                type="button"
                onClick={() => {
                  setTab(i)
                  setFuenteSel(null)
                }}
                className={cn(
                  "-mb-[1.5px] flex items-center gap-2 border-b-[2.5px] px-4 py-[11px] text-sm transition-colors",
                  active
                    ? "border-primary text-foreground font-bold"
                    : "text-label hover:text-foreground border-transparent font-medium",
                )}
              >
                {g.categoria}
                <span
                  className={cn(
                    "rounded-[20px] px-2 py-px text-[11px] font-bold",
                    active
                      ? "text-primary bg-[#FFEAE0] dark:bg-[rgba(255,69,0,.16)] dark:text-[#FF7A4D]"
                      : "bg-muted text-muted-faint",
                  )}
                >
                  {count}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* resumen */}
      {!fuentesQ.isLoading && (
        <div className="text-label mb-[18px] text-[13px]">
          <span className="text-muted-foreground font-semibold">
            {totalPubs.toLocaleString("es-MX")}
          </span>{" "}
          publicaciones en {grupos.flatMap((g) => g.fuentes).length} fuentes monitoreadas.
        </div>
      )}

      {/* fuentes del grupo activo */}
      {fuentesQ.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[140px] rounded-[14px]" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {grupoActivo?.fuentes.map((f) => (
            <FuenteCard
              key={f.clave}
              fuente={f}
              activo={fuenteSel === f.nombre}
              onClick={() =>
                setFuenteSel((s) => (s === f.nombre ? null : f.publicaciones > 0 ? f.nombre : s))
              }
            />
          ))}
        </div>
      )}

      {/* publicaciones de la fuente seleccionada */}
      {fuenteSel && (
        <div className="mt-8">
          <div className="mb-3.5 flex items-center justify-between">
            <div className={sectionLabel}>
              Publicaciones recientes · <span className="text-foreground">{fuenteSel}</span>
            </div>
            <button
              type="button"
              onClick={() => setFuenteSel(null)}
              className="text-primary text-[12.5px] font-semibold"
            >
              Cerrar
            </button>
          </div>
          {pubsQ.isLoading ? (
            <div className="flex flex-col gap-2.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-[64px] w-full rounded-xl" />
              ))}
            </div>
          ) : (pubsQ.data?.items.length ?? 0) === 0 ? (
            <div className="text-muted-faint py-10 text-center text-sm">
              Sin publicaciones para esta fuente.
            </div>
          ) : (
            <div className={`${card} overflow-hidden`}>
              {pubsQ.data?.items.map((p, i, arr) => {
                const badge = riesgoBadge(p.nivel_riesgo)
                return (
                  <a
                    key={p.id}
                    href={p.url_origen ?? "#"}
                    target={p.url_origen ? "_blank" : undefined}
                    rel="noopener noreferrer"
                    className={cn(
                      "hover:bg-muted/40 flex items-center gap-4 px-5 py-[14px] transition-colors",
                      i < arr.length - 1 && "border-border/50 border-b",
                    )}
                  >
                    <span
                      className="shrink-0 rounded-md px-[9px] py-[3px] text-[11px] font-bold"
                      style={{ color: badge.color, background: badge.bg }}
                    >
                      {p.nivel_riesgo ?? "—"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div
                        className="text-foreground truncate text-[14.5px] leading-snug"
                        style={{
                          fontFamily: "var(--font-newsreader), Georgia, serif",
                          fontWeight: 500,
                        }}
                      >
                        {p.titulo}
                      </div>
                      <div className="text-muted-faint mt-0.5 text-xs font-medium">
                        {[p.sector, p.tipo_documento].filter(Boolean).join(" · ")}
                      </div>
                    </div>
                    <span className="text-muted-faint shrink-0 text-[12.5px] font-medium">
                      {p.fecha_publicacion ?? "—"}
                    </span>
                  </a>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function FuenteCard({
  fuente,
  activo,
  onClick,
}: {
  fuente: Fuente
  activo: boolean
  onClick: () => void
}) {
  const badge = estadoBadge(fuente.estado)
  const clickable = fuente.publicaciones > 0
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!clickable}
      className={cn(
        "flex flex-col p-[18px] text-left transition",
        card,
        clickable &&
          "cursor-pointer hover:-translate-y-px hover:shadow-[0_6px_18px_rgba(86,0,4,.07)]",
        !clickable && "opacity-75",
        activo && "ring-primary ring-2",
      )}
    >
      <div className="mb-[11px] flex items-center justify-between gap-2">
        <span className="rounded-[7px] bg-[#FBEDE9] px-[9px] py-1 text-xs font-extrabold tracking-wide text-[#560004] dark:bg-[rgba(255,69,0,.14)] dark:text-[#FF9166]">
          {fuente.clave}
        </span>
        <span
          className="flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10.5px] font-bold"
          style={{ color: badge.color, background: badge.bg }}
        >
          <span className="size-1.5 rounded-full" style={{ background: badge.dot }} />
          {fuente.estado}
        </span>
      </div>
      <div className="text-foreground mb-2 min-h-[36px] text-[13.5px] leading-tight font-semibold">
        {fuente.nombre}
      </div>
      {fuente.nota && (
        <div className="text-muted-faint mb-3 line-clamp-2 text-[11.5px] leading-snug">
          {fuente.nota}
        </div>
      )}
      <div className="border-border/60 mt-auto flex items-center justify-between border-t pt-2.5">
        <span className="text-label text-xs font-medium">{fuente.publicaciones} publicaciones</span>
        {clickable && <ChevronRightIcon className="text-muted-faint size-[15px]" />}
      </div>
    </button>
  )
}
