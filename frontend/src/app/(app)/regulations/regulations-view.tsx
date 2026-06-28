"use client"

import { useEffect, useMemo, useState } from "react"
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import {
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  SearchIcon,
  StarIcon,
} from "lucide-react"

import { riesgoBadge, sectorColor } from "@/lib/brand"
import { stratex } from "@/lib/stratex/client"
import type { Publicacion } from "@/lib/stratex/schemas"
import { Skeleton } from "@/components/ui/skeleton"

const sectionLabel = "text-xs font-bold uppercase tracking-[.14em] text-label"
const card = "rounded-[14px] border border-border bg-card"
const pill =
  "rounded-[20px] border border-border bg-muted px-[11px] py-[3px] text-[11.5px] font-medium text-muted-foreground"
const selectCls =
  "h-[42px] cursor-pointer appearance-none rounded-[10px] border border-border bg-card pr-[38px] pl-3.5 text-[13.5px] font-medium text-foreground outline-none"

const PAGE_SIZE = 20
const C = 2 * Math.PI * 60
const RIESGO_OPTIONS = ["Crítico", "Alto", "Medio", "Bajo", "Solo monitoreo"]

/** Debounce simple para la búsqueda. */
function useDebounced<T>(value: T, ms = 350): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

export function RegulationsView() {
  const [sector, setSector] = useState("")
  const [relevancia, setRelevancia] = useState("")
  const [riesgo, setRiesgo] = useState("")
  const [empresa, setEmpresa] = useState("")
  const [q, setQ] = useState("")
  const [page, setPage] = useState(0)
  const [seguidos, setSeguidos] = useState<Set<string>>(new Set())
  const [abierta, setAbierta] = useState<string | null>(null)

  const qDebounced = useDebounced(q)

  // Reinicia la paginación cuando cambian los filtros (ajuste en render, sin efecto).
  const filtersKey = `${sector}|${relevancia}|${riesgo}|${empresa}|${qDebounced}`
  const [prevFiltersKey, setPrevFiltersKey] = useState(filtersKey)
  if (filtersKey !== prevFiltersKey) {
    setPrevFiltersKey(filtersKey)
    setPage(0)
  }

  const statsQ = useQuery({ queryKey: ["stats"], queryFn: stratex.getStats })
  const empresasQ = useQuery({ queryKey: ["empresas"], queryFn: stratex.getEmpresas })

  const filters = {
    sector: sector || undefined,
    nivel: relevancia || undefined,
    riesgo: riesgo || undefined,
    empresa: empresa || undefined,
    q: qDebounced || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  }
  const pubsQ = useQuery({
    queryKey: ["publicaciones", filters],
    queryFn: () => stratex.getPublicaciones(filters),
    placeholderData: keepPreviousData,
  })

  function toggleFollow(id: string) {
    setSeguidos((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const stats = statsQ.data
  const items = pubsQ.data?.items ?? []
  const total = pubsQ.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const sectorOptions = useMemo(() => (stats ? Object.keys(stats.por_sector).sort() : []), [stats])

  const { dist, donut, totalPie } = useMemo(() => {
    const entries = stats ? Object.entries(stats.por_sector) : []
    const dist = entries
      .map(([name, count]) => ({ name, count, color: sectorColor(name) }))
      .sort((a, b) => b.count - a.count)
    const totalPie = Math.max(
      1,
      dist.reduce((s, d) => s + d.count, 0),
    )
    const visible = dist.filter((d) => d.count > 0)
    const prefix = visible.reduce<number[]>((acc, _d, i) => {
      acc.push((acc[i - 1] ?? 0) + (i === 0 ? 0 : visible[i - 1].count / totalPie))
      return acc
    }, [])
    const donut = visible.map((d, i) => {
      const frac = d.count / totalPie
      return {
        ...d,
        pct: Math.round(frac * 100),
        dash: `${(frac * C).toFixed(2)} ${(C - frac * C).toFixed(2)}`,
        offset: (-prefix[i] * C).toFixed(2),
      }
    })
    return { dist, donut, totalPie }
  }, [stats])

  const maxCount = Math.max(1, ...dist.map((d) => d.count))

  // Destacadas: relevancia Alta (primera página, sin filtros server-side adicionales).
  const featuredQ = useQuery({
    queryKey: ["publicaciones", "destacadas"],
    queryFn: () => stratex.getPublicaciones({ nivel: "Alta", limit: 3 }),
  })
  const featured = featuredQ.data?.items ?? []

  return (
    <div>
      {/* page header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-foreground text-[25px] font-bold tracking-tight">Regulaciones</h1>
          <p className="text-muted-foreground mt-1.5 text-sm">
            Publicaciones regulatorias clasificadas por{" "}
            <em className="serif">sector, relevancia y riesgo</em>, con análisis de IA.
          </p>
        </div>
        <div className="border-border bg-card flex h-10 items-center gap-2 rounded-[10px] border px-3.5 text-[12.5px] font-semibold text-[#3C6B1A] dark:text-[#A7D98A]">
          <span
            className="size-[7px] rounded-full bg-[#4E9A2A]"
            style={{ boxShadow: "0 0 0 3px rgba(78,154,42,.16)" }}
          />
          {stats ? `${stats.total} publicaciones monitoreadas` : "Conectando…"}
        </div>
      </div>

      {/* PRIORIDAD DE CUMPLIMIENTO */}
      <div className="mb-3 flex items-center justify-between">
        <div className={sectionLabel}>Prioridad de cumplimiento</div>
        <div className="text-muted-faint text-[12.5px] font-medium">
          relevancia <span className="font-semibold text-[#C13B2A]">Alta</span>
        </div>
      </div>
      <div className="mb-[30px] grid gap-[18px] md:grid-cols-3">
        {featuredQ.isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className={`${card} p-[18px_20px]`}>
                <Skeleton className="mb-3 h-5 w-24" />
                <Skeleton className="mb-2 h-5 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ))
          : featured.map((c) => {
              const badge = riesgoBadge(c.nivel_riesgo)
              return (
                <div
                  key={c.id}
                  className="border-border bg-card flex flex-col rounded-[14px] border p-[18px_20px_20px]"
                  style={{ borderTop: "3px solid #C13B2A" }}
                >
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="bg-muted text-muted-foreground rounded-[5px] px-[7px] py-0.5 text-[10.5px] font-bold tracking-wide">
                      {c.fuente}
                    </span>
                    <span
                      className="rounded-md px-[9px] py-0.5 text-[11px] font-semibold"
                      style={{ color: badge.color, background: badge.bg }}
                    >
                      {c.nivel_riesgo ?? "—"}
                    </span>
                    {c.sector && <span className="text-label text-xs font-medium">{c.sector}</span>}
                  </div>
                  <div className="text-foreground mb-2.5 text-[15.5px] leading-[1.35] font-semibold">
                    {c.titulo}
                  </div>
                  <div className="text-muted-foreground mb-3.5 line-clamp-6 text-[13px] leading-[1.55]">
                    {c.resumen_ia ?? c.por_que_importa ?? ""}
                  </div>
                  <div className="mt-auto flex flex-wrap gap-1.5">
                    {c.entidades.slice(0, 4).map((e) => (
                      <span key={e} className={pill}>
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              )
            })}
        {!featuredQ.isLoading && featured.length === 0 && (
          <div className="text-muted-faint py-6 text-center text-sm md:col-span-3">
            Sin publicaciones de relevancia alta por ahora.
          </div>
        )}
      </div>

      {/* DISTRIBUCIÓN POR SECTOR */}
      <div className={`${sectionLabel} mb-3`}>Distribución por sector</div>
      <div className="mb-[30px] grid gap-[18px] lg:grid-cols-2">
        <div className={`${card} flex items-center gap-[26px] p-[22px_24px]`}>
          {statsQ.isLoading ? (
            <Skeleton className="size-[172px] rounded-full" />
          ) : (
            <div className="relative size-[172px] shrink-0">
              <svg viewBox="0 0 160 160" className="size-[172px] -rotate-90">
                {donut.map((seg) => (
                  <circle
                    key={seg.name}
                    cx="80"
                    cy="80"
                    r="60"
                    fill="none"
                    stroke={seg.color}
                    strokeWidth="24"
                    strokeDasharray={seg.dash}
                    strokeDashoffset={seg.offset}
                  />
                ))}
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="tnum text-foreground text-[32px] leading-none font-bold">
                  {totalPie}
                </div>
                <div className="text-muted-faint mt-[3px] text-[11px] font-medium">
                  publicaciones
                </div>
              </div>
            </div>
          )}
          <div className="flex min-w-0 flex-1 flex-col gap-[11px]">
            {donut.slice(0, 7).map((seg) => (
              <div key={seg.name} className="flex items-center gap-2.5">
                <span
                  className="size-[11px] shrink-0 rounded-[3px]"
                  style={{ background: seg.color }}
                />
                <span className="text-foreground min-w-0 flex-1 truncate text-[12.5px] font-medium">
                  {seg.name}
                </span>
                <span className="tnum text-muted-foreground text-[13px] font-semibold">
                  {seg.pct}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className={`${card} flex flex-col justify-center gap-[15px] p-[22px_24px]`}>
          {statsQ.isLoading
            ? Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-[16px] w-full" />
              ))
            : dist.slice(0, 8).map((d) => (
                <div key={d.name} className="flex items-center gap-3.5">
                  <div className="text-foreground w-[148px] shrink-0 truncate text-right text-xs font-medium">
                    {d.name}
                  </div>
                  <div className="h-[11px] flex-1 overflow-hidden rounded-md bg-[#F2EBE6] dark:bg-[#2E2320]">
                    <div
                      className="h-full rounded-md"
                      style={{
                        background: d.color,
                        width: `${Math.max(6, Math.round((d.count / maxCount) * 100))}%`,
                      }}
                    />
                  </div>
                  <div className="tnum text-muted-foreground w-6 shrink-0 text-right text-[13px] font-semibold">
                    {d.count}
                  </div>
                </div>
              ))}
        </div>
      </div>

      {/* REGISTRO DE PUBLICACIONES */}
      <div className="mb-3 flex items-center justify-between">
        <div className={sectionLabel}>Registro de publicaciones</div>
        <div className="flex items-center gap-3.5">
          {seguidos.size > 0 && (
            <div className="flex items-center gap-1.5 text-[12.5px] font-semibold text-[#B07A1E]">
              <StarIcon className="size-3.5 fill-[#E0A400] text-[#E0A400]" />
              {seguidos.size} en seguimiento
            </div>
          )}
          <div className="text-muted-faint text-[12.5px] font-semibold">
            <span className="text-muted-foreground">{total.toLocaleString("es-MX")}</span>{" "}
            resultados
          </div>
        </div>
      </div>

      {/* filtros */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <FilterSelect
          value={sector}
          onChange={setSector}
          placeholder="Todos los sectores"
          minW={185}
        >
          {sectorOptions.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect
          value={relevancia}
          onChange={setRelevancia}
          placeholder="Toda relevancia"
          minW={150}
        >
          <option value="Alta">Alta</option>
          <option value="Media">Media</option>
          <option value="Baja">Baja</option>
        </FilterSelect>
        <FilterSelect value={riesgo} onChange={setRiesgo} placeholder="Todo riesgo" minW={150}>
          {RIESGO_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect
          value={empresa}
          onChange={setEmpresa}
          placeholder="Todas las empresas"
          minW={170}
        >
          {(empresasQ.data?.items ?? []).map((e) => (
            <option key={e.nombre} value={e.nombre}>
              {e.nombre}
            </option>
          ))}
        </FilterSelect>
        <div className="relative flex min-w-[220px] flex-1 items-center">
          <SearchIcon className="text-muted-faint pointer-events-none absolute left-3.5 size-[17px]" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar en título o resumen…"
            className="border-border bg-card text-foreground focus:border-primary h-[42px] w-full rounded-[10px] border pr-3.5 pl-10 text-[13.5px] outline-none"
          />
        </div>
      </div>

      {/* lista */}
      {pubsQ.isLoading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[92px] w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <PublicacionRow
              key={item.id}
              item={item}
              seguido={seguidos.has(item.id)}
              abierta={abierta === item.id}
              onToggleFollow={() => toggleFollow(item.id)}
              onToggleOpen={() => setAbierta((a) => (a === item.id ? null : item.id))}
            />
          ))}
        </div>
      )}

      {!pubsQ.isLoading && items.length === 0 && (
        <div className="text-muted-faint py-[60px] text-center text-sm">
          No se encontraron publicaciones con los filtros aplicados.
        </div>
      )}

      {/* paginación */}
      {total > PAGE_SIZE && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="border-border bg-card text-foreground flex h-9 items-center gap-1.5 rounded-[10px] border px-3.5 text-[13px] font-semibold disabled:opacity-40"
          >
            <ChevronLeftIcon className="size-4" /> Anterior
          </button>
          <span className="text-muted-foreground text-[13px] font-medium">
            Página {page + 1} de {totalPages}
          </span>
          <button
            type="button"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="border-border bg-card text-foreground flex h-9 items-center gap-1.5 rounded-[10px] border px-3.5 text-[13px] font-semibold disabled:opacity-40"
          >
            Siguiente <ChevronRightIcon className="size-4" />
          </button>
        </div>
      )}
    </div>
  )
}

function FilterSelect({
  value,
  onChange,
  placeholder,
  minW,
  children,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
  minW: number
  children: React.ReactNode
}) {
  return (
    <div className="relative flex items-center">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={selectCls}
        style={{ minWidth: minW }}
      >
        <option value="">{placeholder}</option>
        {children}
      </select>
      <ChevronDownIcon className="text-muted-faint pointer-events-none absolute right-3 size-[15px]" />
    </div>
  )
}

function PublicacionRow({
  item,
  seguido,
  abierta,
  onToggleFollow,
  onToggleOpen,
}: {
  item: Publicacion
  seguido: boolean
  abierta: boolean
  onToggleFollow: () => void
  onToggleOpen: () => void
}) {
  const badge = riesgoBadge(item.nivel_riesgo)
  return (
    <div className="border-border bg-card overflow-hidden rounded-xl border">
      <div className="flex">
        <div className="w-[5px] shrink-0" style={{ background: badge.color }} />
        <div className="w-[78px] shrink-0 py-4 pl-4">
          <div className="text-muted-foreground text-[11px] font-bold tracking-wide">
            {item.fuente.length > 10 ? item.fuente.slice(0, 10) + "…" : item.fuente}
          </div>
          <div className="tnum text-muted-faint mt-1 text-xs font-medium">
            {item.fecha_publicacion ?? "—"}
          </div>
        </div>
        <button
          type="button"
          onClick={onToggleOpen}
          className="min-w-0 flex-1 cursor-pointer py-[15px] pr-5 pl-1 text-left"
        >
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className="rounded-md px-[9px] py-0.5 text-[11px] font-semibold"
              style={{ color: badge.color, background: badge.bg }}
            >
              {item.nivel_riesgo ?? "—"}
            </span>
            {item.sector && (
              <span className="text-label text-[12.5px] font-medium">{item.sector}</span>
            )}
            {item.tipo_documento && <span className={pill}>{item.tipo_documento}</span>}
            {item.nivel_relevancia && (
              <span className="text-muted-faint text-[11.5px] font-medium">
                Relevancia {item.nivel_relevancia}
              </span>
            )}
          </div>
          <div
            className="text-foreground mb-[7px] text-[16px] leading-[1.4]"
            style={{ fontFamily: "var(--font-newsreader), Georgia, serif", fontWeight: 500 }}
          >
            {item.titulo}
          </div>
          <div
            className={`text-muted-foreground text-[13px] leading-[1.55] ${abierta ? "" : "line-clamp-2"}`}
          >
            {item.resumen_ia ?? "Sin resumen disponible."}
          </div>
        </button>
        <div className="shrink-0 pt-[15px] pr-4 pl-1">
          <button
            type="button"
            onClick={onToggleFollow}
            title="Dar seguimiento"
            aria-pressed={seguido}
            className="flex size-9 items-center justify-center rounded-[9px] border transition-transform hover:scale-105 active:scale-95"
            style={{
              borderColor: seguido ? "#EBD79A" : "var(--border)",
              background: seguido ? "#FBF1D2" : "var(--card)",
            }}
          >
            <StarIcon
              className="size-[19px]"
              style={{
                fill: seguido ? "#E0A400" : "none",
                color: seguido ? "#E0A400" : "#B7A69E",
              }}
              strokeWidth={1.7}
            />
          </button>
        </div>
      </div>

      {abierta && <PublicacionDetalle item={item} />}
    </div>
  )
}

function PublicacionDetalle({ item }: { item: Publicacion }) {
  const campos: { label: string; value: string | null | undefined }[] = [
    { label: "Por qué le importa a Xignux", value: item.por_que_importa },
    { label: "Impacto potencial", value: item.impacto_potencial },
    { label: "Acción recomendada", value: item.accion_recomendada },
    { label: "Área responsable", value: item.area_responsable },
    { label: "Horizonte de impacto", value: item.horizonte_impacto },
    { label: "Autoridad emisora", value: item.autoridad_emisora },
  ]
  const listas: { label: string; value: string[] }[] = [
    { label: "Empresas afectadas", value: item.empresas_afectadas },
    { label: "Productos afectados", value: item.productos_afectados },
    { label: "Plantas afectadas", value: item.plantas_afectadas },
    { label: "Palabras clave", value: item.palabras_clave },
  ]
  return (
    <div className="border-border/60 bg-muted/30 border-t px-5 py-4 pl-[88px]">
      <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
        {campos
          .filter((c) => c.value)
          .map((c) => (
            <div key={c.label}>
              <div className="text-label text-[11px] font-bold tracking-wide uppercase">
                {c.label}
              </div>
              <div className="text-muted-foreground mt-0.5 text-[13px] leading-[1.5]">
                {c.value}
              </div>
            </div>
          ))}
      </div>
      <div className="mt-4 flex flex-col gap-2.5">
        {listas
          .filter((l) => l.value.length > 0)
          .map((l) => (
            <div key={l.label} className="flex flex-wrap items-center gap-1.5">
              <span className="text-label mr-1 text-[11px] font-bold tracking-wide uppercase">
                {l.label}:
              </span>
              {l.value.map((v) => (
                <span key={v} className={pill}>
                  {v}
                </span>
              ))}
            </div>
          ))}
      </div>
      {(item.url_origen || item.url_pdf) && (
        <div className="mt-4 flex flex-wrap gap-3">
          {item.url_origen && (
            <a
              href={item.url_origen}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary flex items-center gap-1.5 text-[12.5px] font-semibold hover:underline"
            >
              <ExternalLinkIcon className="size-3.5" /> Fuente original
            </a>
          )}
          {item.url_pdf && (
            <a
              href={item.url_pdf}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary flex items-center gap-1.5 text-[12.5px] font-semibold hover:underline"
            >
              <ExternalLinkIcon className="size-3.5" /> PDF
            </a>
          )}
        </div>
      )}
    </div>
  )
}
