import type { ReactNode } from "react"
import { redirect } from "next/navigation"

import { auth, signOut } from "@/auth"
import { AppHeader } from "@/components/shell/app-header"
import { AppSidebar } from "@/components/shell/app-sidebar"
import { initials } from "@/lib/brand"

/** Shell de la aplicación: sidebar (guinda) + header + área de contenido scrollable. */
export default async function AppLayout({ children }: { children: ReactNode }) {
  const session = await auth()
  // El proxy ya protege estas rutas; redundancia defensiva.
  if (!session?.user) redirect("/login")

  const nombre = session.user.nombre ?? session.user.name ?? "Usuario"
  const apellido = session.user.apellido ?? ""
  const fullName = `${nombre} ${apellido}`.trim()
  const role = "Asuntos Regulatorios"

  async function logout() {
    "use server"
    await signOut({ redirectTo: "/login" })
  }

  return (
    <div className="bg-card flex h-svh overflow-hidden">
      <AppSidebar logoutAction={logout} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader
          name={fullName}
          role={role}
          initials={initials(fullName) || "U"}
          logoutAction={logout}
        />
        <main className="bg-background flex-1 overflow-auto px-[30px] py-[26px] pb-[34px]">
          {children}
        </main>
      </div>
    </div>
  )
}
