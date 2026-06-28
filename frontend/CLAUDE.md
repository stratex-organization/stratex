# Stratex — Frontend (`/frontend`)

Frontend de **Stratex**: plataforma de monitoreo y extracción de datos gubernamentales de México.
Consume la **API REST de Python (FastAPI)** del backend; **nunca** accede a la base de datos directamente.

## Stack

- **Next.js 16** (App Router, React Server Components) + **React 19** + **TypeScript** estricto.
- **Tailwind CSS v4** + **shadcn/ui** (componentes en `src/components/ui`, base-color neutral, iconos `lucide-react`).
- **TanStack Query** (datos cliente) y **TanStack Table** (tablas grandes).
- **Recharts** para gráficas (usar el patrón Chart de shadcn).
- **Zod** para validar respuestas de la API y derivar tipos.
- **Auth.js (NextAuth v5)** para autenticación.
- Gestor de paquetes: **pnpm**.

## Estructura

```
src/
├─ app/            # rutas (App Router). Server Components por defecto.
├─ components/
│  ├─ ui/          # shadcn/ui — NO editar a mano; regenerar con la CLI.
│  └─ providers.tsx
├─ lib/
│  ├─ api.ts       # cliente tipado contra la API (usar SIEMPRE para fetch al backend)
│  ├─ env.ts       # validación Zod de env pública
│  └─ utils.ts     # cn()
└─ hooks/
```

## Convenciones

- **Datos del backend**: usar `api()` de `src/lib/api.ts` con un `schema` de Zod. No hacer `fetch` crudo al backend.
- **Server Components por defecto**; `"use client"` solo cuando haya estado/efectos/interacción.
- **TanStack Query** para datos en cliente; preferir fetch en Server Components cuando se pueda.
- **Estilos**: solo Tailwind + tokens de shadcn (`bg-background`, `text-foreground`, etc.). Sin CSS suelto ni colores hardcodeados.
- **Componentes shadcn**: agregar con `pnpm dlx shadcn@latest add <comp>`; no editar archivos en `ui/` salvo necesidad real.
- **Variables de entorno**: solo `NEXT_PUBLIC_*` en cliente; declararlas en `env.ts`. Secretos jamás en el frontend.
- **Idioma**: UI en español (es-MX).

## Autenticación

- **Auth.js (NextAuth v5)** con **Credentials provider** en `src/auth.ts`. La sesión usa estrategia
  **JWT** (cookie httpOnly). El provider llama a la API (`/v1/auth/login`), que valida y emite el
  token; `authorize()` guarda `accessToken` y `mustChangePassword` en la sesión.
- **`src/proxy.ts`** (convención Next 16, antes `middleware.ts`): protege rutas. Sin sesión →
  `/login`; con `mustChangePassword` → fuerza `/cambiar-contrasena`. Públicas: `/login`, `/register`.
- Rutas de auth bajo el route group **`src/app/(auth)/`** (`login`, `register`, `cambiar-contrasena`)
  con server actions (`useActionState`) y formularios en `src/components/auth/`.
- Tras el cambio de contraseña obligatorio, el cliente refresca la sesión con `useSession().update()`
  (callback `jwt` con `trigger === "update"`).
- Tipos de sesión extendidos en `src/types/next-auth.d.ts`.
- Variables: `AUTH_SECRET` (obligatoria), `NEXT_PUBLIC_API_URL`, y opcional `API_INTERNAL_URL`
  (llamadas servidor→backend). Ver `.env.example`.

## Backend (API)

Hay **dos backends** distintos:

1. **Auth** (`../backend/auth`, FastAPI + PostgreSQL): login/registro/cambio de contraseña.
   El frontend lo consume vía `api()` (`src/lib/api.ts`) contra `NEXT_PUBLIC_API_URL`.
   Endpoints: `POST /v1/auth/register`, `POST /v1/auth/login`, `GET /v1/auth/me`,
   `POST /v1/auth/change-password`. Detalles en `../backend/auth/README.md`.

2. **API oficial de Stratex** (Keneth) — contenido RegTech (`/api/*`): publicaciones, stats,
   radar, fuentes, empresas. Se consume vía un **proxy BFF** en `src/app/api/stratex/[...path]/route.ts`
   que reenvía a `STRATEX_API_URL` del lado servidor (evita CORS y reserva la `x-api-key` para
   el servidor). El cliente tipado está en `src/lib/stratex/` (`client.ts` + `schemas.ts` Zod) y
   se usa con TanStack Query en las vistas (`home`, `regulations`, `congress`). Integración en
   **modo solo lectura**; las acciones de escritura (PATCH/POST con `x-api-key`) se añadirán al
   proxy cuando entren en alcance. El proxy queda protegido por el middleware de auth (`proxy.ts`),
   así que solo usuarios autenticados pueden consultarlo.

El frontend **nunca** toca una base de datos directamente.

## Comandos

```bash
pnpm dev            # desarrollo
pnpm build          # build de producción
pnpm lint           # eslint
pnpm typecheck      # tsc --noEmit
pnpm format         # prettier --write
pnpm test           # vitest run
```

## Calidad

- Pre-commit (Husky en la raíz del repo) corre `lint-staged` (eslint --fix + prettier) sobre lo staged en `frontend/`.
- Antes de abrir PR: `pnpm lint && pnpm typecheck && pnpm test` en verde.

## Plugin Frontend Design (Anthropic)

Activo en este repo. Al generar UI: tipografía y color intencionales, layouts con jerarquía y profundidad, evitar la estética genérica de IA. Mantener accesibilidad (Radix/shadcn) y los tokens de tema.
