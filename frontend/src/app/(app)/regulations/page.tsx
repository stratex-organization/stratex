import type { Metadata } from "next"

import { RegulationsView } from "./regulations-view"

export const metadata: Metadata = { title: "Regulaciones · Stratex" }

export default function RegulationsPage() {
  return <RegulationsView />
}
