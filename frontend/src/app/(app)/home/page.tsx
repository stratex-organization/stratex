import type { Metadata } from "next"

import { HomeView } from "./home-view"

export const metadata: Metadata = { title: "Inicio · Stratex" }

export default function HomePage() {
  return <HomeView />
}
