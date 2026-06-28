import { redirect } from "next/navigation"

/** La raíz redirige al panel de inicio. El proxy ya protege la sesión. */
export default function RootPage() {
  redirect("/home")
}
