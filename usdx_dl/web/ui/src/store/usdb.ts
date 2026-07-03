import { apiUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import type { USDBSession } from "@/types/api"
import { atom, onMount } from "nanostores"

export const $usdbSessions = atom<USDBSession[]>([])

onMount($usdbSessions, () => {
  fetchUSDBSessions()
  const interval = setInterval(fetchUSDBSessions, 60_000)
  return () => clearInterval(interval)
})

export async function fetchUSDBSessions() {
  const response = await fetch(apiUrl("/usdb/sessions"))
  if (response.ok) {
    $usdbSessions.set(await response.json())
  } else {
    addError("Failed to fetch USDB sessions", response)
  }
}

export async function checkCookie(cookie: string): Promise<USDBSession | null> {
  const response = await fetch(apiUrl("/usdb/check"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cookie }),
  })
  if (response.ok) {
    return await response.json()
  } else {
    return null
  }
}
