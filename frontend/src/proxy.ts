import { NextResponse } from "next/server"
import { auth } from "@/auth"

// Rutas públicas (sin sesión). El registro es público por ahora.
const PUBLIC_ROUTES = new Set(["/login", "/register"])
const CHANGE_PASSWORD_PATH = "/cambiar-contrasena"

export default auth((req) => {
  const { nextUrl } = req
  const { pathname } = nextUrl
  const isLoggedIn = !!req.auth
  const isPublic = PUBLIC_ROUTES.has(pathname)
  const mustChange = req.auth?.user?.mustChangePassword === true

  // Sin sesión: solo rutas públicas.
  if (!isLoggedIn) {
    if (isPublic) return NextResponse.next()
    return NextResponse.redirect(new URL("/login", nextUrl))
  }

  // Con sesión y cambio de contraseña pendiente: forzar la pantalla de cambio.
  if (mustChange && pathname !== CHANGE_PASSWORD_PATH) {
    return NextResponse.redirect(new URL(CHANGE_PASSWORD_PATH, nextUrl))
  }

  // Con sesión válida: no permitir volver a login/register ni a la pantalla de cambio.
  if (!mustChange && (isPublic || pathname === CHANGE_PASSWORD_PATH)) {
    return NextResponse.redirect(new URL("/home", nextUrl))
  }

  return NextResponse.next()
})

export const config = {
  // Aplica a todo excepto API de auth, assets de Next y archivos con extensión.
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
}
