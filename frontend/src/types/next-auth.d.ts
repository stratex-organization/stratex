import type { DefaultSession } from "next-auth"

declare module "next-auth" {
  interface User {
    nombre?: string
    apellido?: string
    mustChangePassword?: boolean
    accessToken?: string
  }

  interface Session {
    accessToken?: string
    user: {
      id: string
      nombre?: string
      apellido?: string
      mustChangePassword?: boolean
    } & DefaultSession["user"]
  }
}
