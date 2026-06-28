"use client"

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { CalendarIcon, CheckCircle2Icon, ClockIcon, FileTextIcon, TargetIcon } from "lucide-react"

import { riesgoBadge, sectorColor } from "@/lib/brand"
import { stratex } from "@/lib/stratex/client"
import type { Publicacion } from "@/lib/stratex/schemas"
import { Skeleton } from "@/components/ui/skeleton"

const card = "rounded-2xl border border-border bg-card"
const tableCols = "grid grid-cols-[2.6fr_1fr_1.1fr_0.9fr_0.7fr] items-center"

const RIESGO_ALERTA = new Set(["Crítico", "Alto", "Medio"])

function saludo(): string {
  const h = new Date().getHours()
  if (h < 12) return "Buenos días"
  if (h < 19) return "Buenas tardes"
  return "Buenas noches"
}

function fechaHoy(): string {
  return new Intl.DateTimeFormat("es-MX", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date())
}

export function HomeView() {
  const { data: session } = useSession()
  const nombre = session?.user?.name?.split(" ")[0] ?? ""

  const statsQ = useQuery({ queryKey: ["stats"], queryFn: stratex.getStats })
  const radarQ = useQuery({ queryKey: ["radar"], queryFn: stratex.getRadar })
  const recientesQ = useQuery({
    queryKey: ["publicaciones", { recientes: true }],
    queryFn: () => stratex.getPublicaciones({ limit: 6 }),
  })

  const stats = statsQ.data
  const radar = radarQ.data

  const alertasRiesgo = useMemo(() => {
    if (!radar) return 0
    return Object.entries(radar.por_riesgo)
      .filter(([k]) => RIESGO_ALERTA.has(k))
      .reduce((s, [, n]) => s + n, 0)
  }, [radar])

  const sectores = useMemo(() => {
    if (!stats) return []
    return Object.entries(stats.por_sector)
      .map(([name, count]) => ({ name, count, color: sectorColor(name) }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 7)
  }, [stats])

  const maxSector = Math.max(1, ...sectores.map((s) => s.count))
  const criticas = radar?.criticas.slice(0, 5) ?? []
  const recientes = recientesQ.data?.items ?? []

  return (
    <div>
      {/* Saludo */}
      <div className="mb-[22px] flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-foreground text-[25px] font-bold tracking-tight">
            {saludo()}
            <em className="serif">{nombre ? `, ${nombre}` : ""}</em>
          </h1>
          <p className="text-muted-foreground mt-1.5 text-sm">
            Esto es lo que se movió en el panorama regulatorio.
          </p>
        </div>
        <div className="border-border bg-card text-muted-foreground flex h-10 items-center gap-2 rounded-[10px] border px-3.5 text-[13px] font-medium">
          <CalendarIcon className="text-muted-faint size-4" />
          {fechaHoy()}
        </div>
      </div>

      {/* KPIs */}
      <div className="mb-[18px] grid gap-[18px] sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Publicaciones totales"
          value={stats?.total}
          loading={statsQ.isLoading}
          icon={FileTextIcon}
          tint="bg-[#FFEAE0] text-[#FF4500] dark:bg-[rgba(255,69,0,.16)] dark:text-[#FF7A4D]"
          foot="en monitoreo"
        />
        <Kpi
          label="Procesadas por IA"
          value={stats?.procesadas}
          loading={statsQ.isLoading}
          icon={CheckCircle2Icon}
          tint="bg-[#E9F4DD] text-[#3C6B1A] dark:bg-[rgba(173,226,138,.14)] dark:text-[#A7D98A]"
          foot="con análisis completo"
        />
        <Kpi
          label="Pendientes"
          value={stats?.pendientes}
          loading={statsQ.isLoading}
          icon={ClockIcon}
          tint="bg-[#E6EEF6] text-[#2E4178] dark:bg-[rgba(177,206,229,.16)] dark:text-[#A9C6E2]"
          foot="por analizar"
        />
        <Kpi
          label="Alertas de riesgo"
          value={alertasRiesgo}
          loading={radarQ.isLoading}
          icon={TargetIcon}
          tint="bg-[#FBF1D2] text-[#B07A1E] dark:bg-[rgba(216,164,80,.16)] dark:text-[#E0B266]"
          foot="riesgo medio o superior"
        />
      </div>

      {/* Distribución por sector + Radar */}
      <div className="mb-[18px] grid gap-[18px] lg:grid-cols-[1.62fr_1fr]">
        {/* Barras por sector */}
        <div className={`${card} p-[20px_22px]`}>
          <div className="mb-5">
            <div className="text-foreground text-[15px] font-bold">Distribución por sector</div>
            <div className="text-muted-faint mt-0.5 text-[12.5px]">
              Publicaciones clasificadas por sector regulatorio
            </div>
          </div>
          {statsQ.isLoading ? (
            <div className="flex flex-col gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-[18px] w-full" />
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-[15px]">
              {sectores.map((d) => (
                <div key={d.name} className="flex items-center gap-3.5">
                  <div className="text-foreground w-[150px] shrink-0 truncate text-right text-xs font-medium">
                    {d.name}
                  </div>
                  <div className="h-[11px] flex-1 overflow-hidden rounded-md bg-[#F2EBE6] dark:bg-[#2E2320]">
                    <div
                      className="h-full rounded-md"
                      style={{
                        background: d.color,
                        width: `${Math.max(6, Math.round((d.count / maxSector) * 100))}%`,
                      }}
                    />
                  </div>
                  <div className="tnum text-muted-foreground w-7 shrink-0 text-right text-[13px] font-semibold">
                    {d.count}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Radar */}
        <div className={`${card} flex flex-col p-[20px_22px]`}>
          <div className="mb-3.5 flex items-center justify-between">
            <div className="text-foreground text-[15px] font-bold">Radar — alertas críticas</div>
            <a href="/regulations" className="text-primary text-[12.5px] font-semibold">
              Ver todo
            </a>
          </div>
          {radarQ.isLoading ? (
            <div className="flex flex-col gap-4 py-1">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[40px] w-full" />
              ))}
            </div>
          ) : criticas.length === 0 ? (
            <div className="text-muted-faint py-8 text-center text-[13px]">
              Sin alertas críticas por ahora.
            </div>
          ) : (
            <div className="flex flex-col">
              {criticas.map((a, i) => {
                const badge = riesgoBadge(a.nivel_riesgo)
                return (
                  <div
                    key={a.id}
                    className={`flex gap-3 py-[13px] ${i < criticas.length - 1 ? "border-border/60 border-b" : ""}`}
                  >
                    <span
                      className="mt-[5px] size-[9px] shrink-0 rounded-full"
                      style={{ background: badge.color }}
                    />
                    <div className="min-w-0">
                      <div className="text-foreground line-clamp-2 text-[13.5px] font-semibold">
                        {a.titulo}
                      </div>
                      <div className="text-muted-faint mt-[3px] text-xs">
                        {[a.sector, a.fuente].filter(Boolean).join(" · ")}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Publicaciones recientes */}
      <div className={`${card} p-[20px_22px]`}>
        <div className="mb-1.5 flex items-center justify-between">
          <div className="text-foreground text-[15px] font-bold">Publicaciones recientes</div>
          <a href="/regulations" className="text-primary text-[12.5px] font-semibold">
            Ir a Regulaciones
          </a>
        </div>
        <div
          className={`${tableCols} border-border/60 text-muted-faint border-b px-2 py-3 text-[11.5px] font-semibold tracking-wide uppercase`}
        >
          <div>Título</div>
          <div>Sector</div>
          <div>Fuente</div>
          <div>Riesgo</div>
          <div className="text-right">Fecha</div>
        </div>
        {recientesQ.isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="px-2 py-[15px]">
                <Skeleton className="h-[18px] w-full" />
              </div>
            ))
          : recientes.map((p: Publicacion, i) => {
              const badge = riesgoBadge(p.nivel_riesgo)
              return (
                <div
                  key={p.id}
                  className={`${tableCols} px-2 py-[15px] ${i < recientes.length - 1 ? "border-border/40 border-b" : ""}`}
                >
                  <div className="text-foreground truncate pr-3 text-[13.5px] font-semibold">
                    {p.titulo}
                  </div>
                  <div className="text-muted-foreground truncate pr-2 text-[13px] font-medium">
                    {p.sector ?? "—"}
                  </div>
                  <div className="text-muted-foreground truncate pr-2 text-[13px] font-medium">
                    {p.fuente}
                  </div>
                  <div>
                    <span
                      className="rounded-md px-2.5 py-[3px] text-[11.5px] font-semibold"
                      style={{ color: badge.color, background: badge.bg }}
                    >
                      {p.nivel_riesgo ?? "—"}
                    </span>
                  </div>
                  <div className="tnum text-muted-faint text-right text-[12.5px] font-medium">
                    {p.fecha_publicacion ?? "—"}
                  </div>
                </div>
              )
            })}
        {!recientesQ.isLoading && recientes.length === 0 && (
          <div className="text-muted-faint py-8 text-center text-[13px]">
            No hay publicaciones todavía.
          </div>
        )}
      </div>
    </div>
  )
}

function Kpi({
  label,
  value,
  loading,
  icon: Icon,
  tint,
  foot,
}: {
  label: string
  value: number | undefined
  loading: boolean
  icon: typeof FileTextIcon
  tint: string
  foot: string
}) {
  return (
    <div className={`${card} p-[18px_20px]`}>
      <div className="flex items-center justify-between">
        <span className="text-label text-[12.5px] font-semibold">{label}</span>
        <span className={`flex size-8 items-center justify-center rounded-[9px] ${tint}`}>
          <Icon className="size-[17px]" strokeWidth={1.9} />
        </span>
      </div>
      <div className="tnum text-foreground mt-3 text-[32px] font-bold tracking-tight">
        {loading ? <Skeleton className="h-[34px] w-16" /> : (value ?? 0).toLocaleString("es-MX")}
      </div>
      <div className="text-muted-faint mt-2 text-xs">{foot}</div>
    </div>
  )
}
