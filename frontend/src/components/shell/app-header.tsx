"use client"

import { useState } from "react"
import { BellIcon, ChevronDownIcon, LogOutIcon, SearchIcon } from "lucide-react"

import { ThemeToggle } from "@/components/shell/theme-toggle"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

function FlagMX() {
  return (
    <svg width="20" height="14" viewBox="0 0 18 12" aria-hidden>
      <rect width="6" height="12" x="0" fill="#006847" />
      <rect width="6" height="12" x="6" fill="#fff" />
      <rect width="6" height="12" x="12" fill="#CE1126" />
    </svg>
  )
}

function FlagUS() {
  return (
    <svg width="20" height="14" viewBox="0 0 18 12" aria-hidden>
      <rect width="18" height="12" fill="#fff" />
      <rect width="18" height="12" fill="#B22234" />
      {[1, 3, 5, 7, 9].map((i) => (
        <rect key={i} y={i * 1.2} width="18" height="1.2" fill="#fff" />
      ))}
      <rect width="8" height="6.5" fill="#3C3B6E" />
    </svg>
  )
}

const LANGS = [
  { code: "MEX", label: "Español", flag: <FlagMX /> },
  { code: "US", label: "English", flag: <FlagUS /> },
] as const

type AppHeaderProps = {
  name: string
  role: string
  initials: string
  logoutAction: () => Promise<void>
}

const iconBtn =
  "flex size-10 items-center justify-center rounded-[11px] border border-border bg-card text-muted-foreground transition-colors hover:text-foreground"

export function AppHeader({ name, role, initials, logoutAction }: AppHeaderProps) {
  const [lang, setLang] = useState<(typeof LANGS)[number]>(LANGS[0])

  return (
    <header className="border-border bg-card flex h-[66px] shrink-0 items-center gap-[18px] border-b px-[26px]">
      {/* Buscador */}
      <div className="border-border bg-muted text-muted-faint flex h-10 w-[330px] items-center gap-[9px] rounded-[11px] border px-3.5">
        <SearchIcon className="size-[17px]" />
        <span className="text-[13.5px]">Buscar regulaciones, proyectos…</span>
      </div>

      <div className="ml-auto flex items-center gap-[13px]">
        <ThemeToggle />

        {/* Selector de idioma */}
        <DropdownMenu>
          <DropdownMenuTrigger className="border-border bg-card flex h-10 cursor-pointer items-center gap-[9px] rounded-[11px] border px-3 outline-none">
            {lang.flag}
            <span className="text-foreground text-[13px] font-semibold">{lang.label}</span>
            <span className="text-muted-faint text-[11px] font-semibold">{lang.code}</span>
            <ChevronDownIcon className="text-muted-faint size-3.5" strokeWidth={2.4} />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[180px]">
            {LANGS.map((l) => (
              <DropdownMenuItem key={l.code} onClick={() => setLang(l)} className="gap-2.5">
                {l.flag}
                <span className="font-medium">{l.label}</span>
                <span className="text-muted-faint ml-auto text-xs">{l.code}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Notificaciones */}
        <button type="button" className={iconBtn + " relative"} aria-label="Notificaciones">
          <BellIcon className="size-[19px]" />
          <span className="border-card bg-primary absolute top-2 right-[9px] size-[7px] rounded-full border-2" />
        </button>

        <div className="bg-border h-[30px] w-px" />

        {/* Perfil */}
        <DropdownMenu>
          <DropdownMenuTrigger className="flex cursor-pointer items-center gap-[11px] outline-none">
            <div
              className="flex size-[38px] items-center justify-center rounded-[11px] text-sm font-bold text-white"
              style={{ background: "linear-gradient(145deg,#FF4500,#B81A06)" }}
            >
              {initials}
            </div>
            <div className="hidden text-left leading-[1.15] sm:block">
              <div className="text-foreground text-[13.5px] font-semibold">{name}</div>
              <div className="text-muted-faint text-[11.5px] font-medium">{role}</div>
            </div>
            <ChevronDownIcon className="text-muted-faint size-3.5" strokeWidth={2.4} />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[200px]">
            <div className="px-2 py-1.5">
              <div className="text-foreground text-sm font-semibold">{name}</div>
              <div className="text-muted-faint text-xs">{role}</div>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive" onClick={() => logoutAction()}>
              <LogOutIcon className="size-4" />
              Cerrar sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
