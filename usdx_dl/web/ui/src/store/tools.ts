import { deepEqual } from "@/lib/cmp"
import { apiUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import { fetchServerConfig } from "@/store/settings"
import type { Tool } from "@/types/api"
import { atom, map, onMount } from "nanostores"

export const $tools = atom<Tool[]>([])
export const $downloadProgress = map<{ [key: string]: number }>({})

onMount($tools, () => {
  fetchTools()
  const removeListener = $tools.listen((value, oldValue) => {
    console.log("tools changed", value, oldValue)
    if (!deepEqual(value, oldValue)) {
      fetchServerConfig()
    }
  })
  const handle = setInterval(fetchTools, 60_000)
  return () => {
    removeListener()
    clearInterval(handle)
  }
})

async function fetchTools() {
  const response = await fetch(apiUrl("/tools"))
  if (response.ok) {
    $tools.set(await response.json())
    for (const tool of $tools.get()) {
      if ([undefined, 0, 100].includes($downloadProgress.get()[tool.name])) {
        $downloadProgress.setKey(tool.name, tool.downloadRequired ? 0 : 100)
      }
    }
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
