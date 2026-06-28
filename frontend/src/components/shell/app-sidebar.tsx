"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ChevronDownIcon,
  FileTextIcon,
  HouseIcon,
  Layers3Icon,
  LandmarkIcon,
  LogOutIcon,
  MessageCircleIcon,
  TargetIcon,
  type LucideIcon,
} from "lucide-react"

import { BrandMark } from "@/components/brand-mark"
import { cn } from "@/lib/utils"

type NavItem = {
  label: string
  href: string
  icon: LucideIcon
  badge?: string
}

const NAV: NavItem[] = [
  { label: "Inicio", href: "/home", icon: HouseIcon },
  { label: "Regulaciones", href: "/regulations", icon: FileTextIcon },
  { label: "Congreso", href: "/congress", icon: LandmarkIcon },
]

const SECONDARY: NavItem[] = [
  { label: "Radar Legislativo", href: "#", icon: TargetIcon },
  { label: "Stratex Chat", href: "#", icon: MessageCircleIcon, badge: "AI" },
]

const itemBase =
  "flex items-center gap-3 rounded-[10px] px-[13px] py-[11px] text-sm transition-colors"

export function AppSidebar({ logoutAction }: { logoutAction: () => Promise<void> }) {
  const pathname = usePathname()
  const [projectsOpen, setProjectsOpen] = useState(false)

  const isActive = (href: string) => href !== "#" && pathname.startsWith(href)

  function navClass(active: boolean) {
    return cn(
      itemBase,
      active
        ? "bg-primary font-semibold text-primary-foreground shadow-[0_6px_16px_rgba(255,69,0,.34)]"
        : "font-medium text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
    )
  }

  return (
    <aside className="bg-sidebar flex w-[258px] shrink-0 flex-col">
      <div className="px-[22px] pt-5 pb-[18px]">
        <BrandMark titleClassName="text-white" />
      </div>
      <div className="bg-sidebar-border mx-[18px] mt-0.5 mb-3 h-px" />

      <nav className="flex flex-1 flex-col gap-[3px] overflow-auto px-[14px]">
        <div className="text-sidebar-muted px-3 pt-2 pb-1.5 text-[10.5px] font-semibold tracking-[.14em] uppercase">
          Plataforma
        </div>

        {NAV.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link key={item.label} href={item.href} className={navClass(active)}>
              <Icon className="size-[19px]" strokeWidth={active ? 2 : 1.8} />
              {item.label}
            </Link>
          )
        })}

        {/* Proyectos Ley — expandible */}
        <button
          type="button"
          onClick={() => setProjectsOpen((v) => !v)}
          className={cn(
            itemBase,
            "text-sidebar-accent-foreground font-semibold",
            projectsOpen ? "bg-sidebar-accent" : "text-sidebar-foreground hover:bg-sidebar-accent",
          )}
        >
          <Layers3Icon className="size-[19px]" strokeWidth={1.8} />
          Proyectos Ley
          <ChevronDownIcon
            className={cn(
              "text-sidebar-muted ml-auto size-[15px] transition-transform",
              projectsOpen && "rotate-180",
            )}
            strokeWidth={2.2}
          />
        </button>
        {projectsOpen && (
          <div className="border-sidebar-border my-0.5 ml-[30px] flex flex-col gap-0.5 border-l-[1.5px] pl-3">
            {["Federal", "Estatal"].map((sub) => (
              <Link
                key={sub}
                href="#"
                className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-lg px-3 py-2 text-[13.5px] font-medium transition-colors"
              >
                {sub}
              </Link>
            ))}
          </div>
        )}

        {SECONDARY.map((item) => {
          const Icon = item.icon
          return (
            <Link key={item.label} href={item.href} className={navClass(false)}>
              <Icon className="size-[19px]" strokeWidth={1.8} />
              {item.label}
              {item.badge && (
                <span
                  className="ml-auto rounded-md px-[7px] py-0.5 text-[10px] font-bold tracking-wide text-[#FFD2C4]"
                  style={{ background: "rgba(255,69,0,.3)" }}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      <div className="border-sidebar-border border-t px-[18px] py-[18px]">
        <form action={logoutAction}>
          <button
            type="submit"
            className={cn(itemBase, "hover:bg-sidebar-accent w-full font-medium text-[#EAA994]")}
          >
            <LogOutIcon className="size-[19px]" strokeWidth={1.8} />
            Cerrar sesión
          </button>
        </form>
      </div>
    </aside>
  )
}
