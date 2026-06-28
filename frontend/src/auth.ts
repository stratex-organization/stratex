import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

/**
 * URL del backend para llamadas servidor→servidor. En despliegues separados puede diferir de la
 * pública; cae a NEXT_PUBLIC_API_URL si no se define.
 */
const API_URL = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL

type BackendLogin = {
  access_token: string
  token_type: string
  user: {
    id: string
    nombre: string
    apellido: string
    email: string
    must_change_password: boolean
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: {
        email: { label: "Correo", type: "email" },
        password: { label: "Contraseña", type: "password" },
      },
      authorize: async (credentials) => {
        const email = credentials?.email
        const password = credentials?.password
        if (typeof email !== "string" || typeof password !== "string") return null

        const res = await fetch(`${API_URL}/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        })
        if (!res.ok) return null

        const data = (await res.json()) as BackendLogin
        return {
          id: data.user.id,
          email: data.user.email,
          name: `${data.user.nombre} ${data.user.apellido}`,
          nombre: data.user.nombre,
          apellido: data.user.apellido,
          mustChangePassword: data.user.must_change_password,
          accessToken: data.access_token,
        }
      },
    }),
  ],
  callbacks: {
    jwt: async ({ token, user, trigger, session }) => {
      if (user) {
        token.id = user.id as string
        token.nombre = user.nombre
        token.apellido = user.apellido
        token.mustChangePassword = user.mustChangePassword
        token.accessToken = user.accessToken
      }
      // Refresco de sesión tras cambiar la contraseña (useSession().update()).
      if (trigger === "update" && session?.mustChangePassword === false) {
        token.mustChangePassword = false
      }
      return token
    },
    session: async ({ session, token }) => {
      // JWT extiende Record<string, unknown>; tipamos las lecturas explícitamente.
      session.user.id = token.id as string
      session.user.nombre = token.nombre as string | undefined
      session.user.apellido = token.apellido as string | undefined
      session.user.mustChangePassword = token.mustChangePassword as boolean | undefined
      session.accessToken = token.accessToken as string | undefined
      return session
    },
  },
})
