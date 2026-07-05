import { apiUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import { $activeTab } from "@/store/nav"
import type { PipelineContext, ServerState } from "@/types/api"
import { map, onMount } from "nanostores"

export const $state = map<ServerState>({ processing: null, queue: [], pending: 0 })

onMount($state, () => {
  fetchState()
  const handle = setInterval(fetchState, import.meta.env.DEV ? 5000 : 1000)
  return () => clearInterval(handle)
})

async function fetchState() {
  const response = await fetch(apiUrl("/state"))
  if (response.ok) {
    $state.set(await response.json())
  } else {
    await addError("Failed to fetch state", response)
  }
}

async function queueApiRequest(fetchPromise: Promise<Response>) {
  try {
    const response = await fetchPromise
    if (response.ok) {
      await fetchState()
    } else {
      await addError("Failed to update queue", response)
    }
  } finally {
  }
}

export async function addToQueue(link: string) {
  if (!link) {
    return
  }
  await queueApiRequest(
    fetch(apiUrl("/queue/add"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: link }),
    }),
  )
  link = ""
  $activeTab.set("tab-queue")
}

export async function removeFromQueue(item: PipelineContext) {
  await queueApiRequest(
    fetch(apiUrl("/queue/remove"), {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
}

export async function moveQueueItem(
  item: PipelineContext,
  direction: "up" | "down",
  toEnd: boolean,
) {
  await queueApiRequest(
    fetch(apiUrl("/queue/move"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item, direction, toEnd }),
    }),
  )
}

export async function updateQueueItem(item: PipelineContext, done: () => void) {
  await queueApiRequest(
    fetch(apiUrl("/queue/update"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
  done()
}

export async function retryQueueItem(item: PipelineContext) {
  await queueApiRequest(
    fetch(apiUrl("/queue/retry"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
}
