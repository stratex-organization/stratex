"use client"

import { useEffect, useState } from "react"
import { MoonIcon, SunIcon } from "lucide-react"
import { useTheme } from "next-themes"

/** Botón 40×40 que alterna modo claro/oscuro (luna en claro, sol en oscuro). */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  // Evita el mismatch de hidratación: el tema resuelto solo se conoce en cliente.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true)
  }, [])

  const isDark = resolvedTheme === "dark"

  return (
    <button
      type="button"
      title={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      aria-label="Cambiar tema"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="border-border bg-card text-muted-foreground hover:text-foreground flex size-10 items-center justify-center rounded-[11px] border transition-colors"
    >
      {mounted && isDark ? (
        <SunIcon className="size-[19px]" />
      ) : (
        <MoonIcon className="size-[19px]" />
      )}
    </button>
  )
}
