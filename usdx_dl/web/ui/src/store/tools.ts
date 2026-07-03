import { apiUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import type { Tool } from "@/types/api"
import { atom, onMount } from "nanostores"

export const $tools = atom<Tool[]>([])

onMount($tools, () => {
  fetchTools()
  const handle = setInterval(fetchTools, 60_000)
  return () => clearInterval(handle)
})

async function fetchTools() {
  const response = await fetch(apiUrl("/tools"))
  if (response.ok) {
    $tools.set(await response.json())
  } else {
    await addError("Failed to fetch tools", response)
  }
}

export async function downloadTool(name: string) {
  const response = await fetch(apiUrl("/tools/download"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  })
  if (response.ok) {
    await fetchTools()
  } else {
    await addError(`Failed to download ${name}`, response)
  }
}
