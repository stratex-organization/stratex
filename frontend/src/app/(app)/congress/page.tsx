import type { Metadata } from "next"

import { CongressView } from "./congress-view"

export const metadata: Metadata = { title: "Congreso · Stratex" }

export default function CongressPage() {
  return <CongressView />
}
