import { apiUrl } from "@/lib/host"
import { atom } from "nanostores"

export const $logBuffer = atom<string[]>([])

export async function clearLog() {
  $logBuffer.set([])
  await fetch(apiUrl("/log"), { method: "DELETE" })
}
