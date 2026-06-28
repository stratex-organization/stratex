import { type NextRequest, NextResponse } from "next/server"

/**
 * Proxy BFF (Backend-for-Frontend) hacia la API oficial de Stratex (Keneth).
 *
 * El navegador llama a `/api/stratex/<ruta>` y este handler reenvía a
 * `${STRATEX_API_URL}/api/<ruta>` del lado servidor. Beneficios:
 *  - La URL real y la futura `x-api-key` quedan solo en el servidor.
 *  - Evita problemas de CORS (la llamada es servidor→servidor).
 *
 * Solo lectura (GET) en esta fase. Las acciones de escritura (PATCH/POST con
 * x-api-key) se añadirán aquí cuando entren en alcance.
 */

const DEFAULT_STRATEX_API_URL = "https://stratex-api-production.up.railway.app"

function targetBase(): string {
  return (process.env.STRATEX_API_URL ?? DEFAULT_STRATEX_API_URL).replace(/\/$/, "")
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const search = req.nextUrl.search
  const url = `${targetBase()}/api/${path.join("/")}${search}`

  try {
    const upstream = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    })

    const body = await upstream.text()
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
      },
    })
  } catch {
    return NextResponse.json({ detail: "No se pudo contactar la API de Stratex." }, { status: 502 })
  }
}
