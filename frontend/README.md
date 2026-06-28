# Stratex — Frontend (`/frontend`)

Frontend de **Stratex**, plataforma de monitoreo y extracción de datos regulatorios de México.
Es una app **Next.js 16 (App Router)** que consume las **APIs REST** del backend; **nunca** accede
a la base de datos directamente.

> Este módulo es autocontenido y vive en `frontend/`, aislado del backend de contenido (RegTech) en
> la raíz del repo y del servicio de auth en `../backend/auth`. Así cada parte se desarrolla y
> despliega sin pisarse.

## Stack

- **Next.js 16** (App Router, React Server Components) + **React 19** + **TypeScript** estricto
- **Tailwind CSS v4** + **shadcn/ui** (`src/components/ui`, base neutral, iconos `lucide-react`)
- **TanStack Query** (datos en cliente) y **TanStack Table** (tablas)
- **Recharts** para gráficas (patrón Chart de shadcn)
- **Zod** para validar respuestas de la API y derivar tipos
- **Auth.js (NextAuth v5)** para autenticación (estrategia JWT, cookie httpOnly)
- Gestor de paquetes: **pnpm**

## Estructura

```
frontend/
├─ src/
│  ├─ app/                 # rutas (App Router). Server Components por defecto.
│  │  ├─ (app)/            # área autenticada (dashboard, regulations, congress…)
│  │  ├─ (auth)/           # login, register, cambiar-contrasena
│  │  └─ api/              # route handlers (BFF/proxy hacia los backends)
│  ├─ components/
│  │  ├─ ui/               # shadcn/ui — regenerar con la CLI, no editar a mano
│  │  ├─ auth/             # formularios de autenticación
│  │  └─ shell/            # layout/navegación
│  ├─ lib/
│  │  ├─ api.ts            # cliente tipado contra la API de auth
│  │  ├─ stratex/          # cliente tipado (client.ts + schemas.ts) de la API RegTech
│  │  ├─ validations/      # esquemas Zod
│  │  ├─ env.ts            # validación de variables de entorno públicas
│  │  └─ utils.ts          # cn()
│  ├─ types/               # tipos (incl. extensión de sesión next-auth)
│  ├─ auth.ts              # configuración de Auth.js (Credentials provider)
│  └─ proxy.ts             # protección de rutas (convención Next 16, antes middleware.ts)
├─ public/
├─ .env.example            # plantilla de variables de entorno
├─ next.config.ts
├─ package.json
└─ pnpm-lock.yaml
```

## Backends que consume

Hay **dos backends** distintos, y el frontend habla con ambos vía clientes tipados (nunca toca la BD):

1. **Auth** (`../backend/auth`, FastAPI + PostgreSQL): login/registro/cambio de contraseña.
   Se consume con `api()` de `src/lib/api.ts` contra `NEXT_PUBLIC_API_URL`.
   Endpoints: `POST /v1/auth/register`, `POST /v1/auth/login`, `GET /v1/auth/me`,
   `POST /v1/auth/change-password`.
2. **API RegTech de Stratex** (Keneth): publicaciones, stats, radar, fuentes, empresas.
   Se consume vía un **proxy BFF** en `src/app/api/stratex/[...path]/route.ts` que reenvía a
   `STRATEX_API_URL` del lado servidor (evita CORS y reserva la `x-api-key` en el servidor).
   Cliente tipado en `src/lib/stratex/`. Integración en **modo solo lectura** por ahora.

## Puesta en marcha (local)

```bash
pnpm install
cp .env.example .env.local     # rellena los valores (ver más abajo)
pnpm dev                       # http://localhost:3000
```

### Variables de entorno

Declaradas en `.env.example`. Las que necesitas para correr:

| Variable              | Lado     | Descripción                                                        |
| --------------------- | -------- | ------------------------------------------------------------------ |
| `AUTH_SECRET`         | servidor | **Obligatoria.** Secreto de Auth.js. Genera con `npx auth secret`. |
| `NEXT_PUBLIC_API_URL` | cliente  | URL pública de la API de **auth** (FastAPI).                       |
| `API_INTERNAL_URL`    | servidor | _(opcional)_ URL interna servidor→backend de auth.                 |
| `STRATEX_API_URL`     | servidor | URL de la API **RegTech** de Keneth (usada por el proxy BFF).      |
| `STRATEX_API_KEY`     | servidor | _(opcional)_ `x-api-key` para la API RegTech.                      |

> Solo variables `NEXT_PUBLIC_*` llegan al cliente. **Los secretos jamás se exponen al frontend.**

## Comandos

```bash
pnpm dev          # desarrollo
pnpm build        # build de producción
pnpm start        # servir el build
pnpm lint         # eslint
pnpm typecheck    # tsc --noEmit
pnpm format       # prettier --write
pnpm test         # vitest run
```

## Calidad

- Pre-commit (Husky en la raíz del repo, `.husky/pre-commit`) corre `lint-staged` (eslint --fix +
  prettier) sobre lo _staged_ en `frontend/`.
- Antes de abrir PR: `pnpm lint && pnpm typecheck && pnpm test` en verde.
- Convenciones detalladas (datos del backend, Server Components, estilos, auth) en
  [`CLAUDE.md`](CLAUDE.md).

## Despliegue en Vercel

El frontend se despliega en **Vercel** apuntando el _Root Directory_ a `frontend/`.

1. **Importa el repo** en Vercel y selecciona la rama `dev`.
2. **Root Directory:** `frontend` (importante: el repo es un monorepo).
3. **Framework Preset:** Next.js (autodetectado). Build: `pnpm build`. Install: `pnpm install`.
4. **Environment Variables:** carga las de la tabla de arriba (al menos `AUTH_SECRET`,
   `NEXT_PUBLIC_API_URL`, `STRATEX_API_URL`).
5. **Deploy.** Cada push a `dev` genera un _Preview_; producción se ata a la rama que elijas.

Guía paso a paso completa: ver el mensaje de despliegue del equipo o la
[documentación de Next.js en Vercel](https://nextjs.org/docs/app/building-your-application/deploying).
