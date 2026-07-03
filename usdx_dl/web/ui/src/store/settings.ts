import { apiUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import { $activeTab } from "@/store/nav"
import type { ServerConfig, Settings } from "@/types/api"
import { persistentMap } from "@nanostores/persistent"
import { listenKeys, map, onMount } from "nanostores"

export type Setup = {
  songsFolder: boolean
  usdbCookie: boolean
  downloadTools: boolean
}

export const $setup = map<Setup>({
  songsFolder: false,
  usdbCookie: false,
  downloadTools: false,
})
export const $settings = map<Settings>()
export const $serverCfg = map<ServerConfig>()
export const $pin = persistentMap<{ value: string; valid: boolean | null }>(
  "settings:pin:",
  { value: "", valid: null },
  { encode: JSON.stringify, decode: JSON.parse },
)

onMount($settings, () => {
  fetchSettings()
  const handle = setInterval(fetchSettings, 3000)
  $settings.listen(() => updateSettings(false))

  return () => clearInterval(handle)
})

onMount($serverCfg, () => {
  fetchServerConfig()
  return () => {}
})

onMount($pin, () => {
  listenKeys($pin, ["value"], () => updateSettings(true))
})

export async function setupComplete() {
  const response = await fetch(apiUrl("/setup/complete"), { method: "POST" })
  if (response.ok) {
    await fetchServerConfig() // switch page
    await fetchSettings()
  } else {
    await addError("Failed to mark setup as complete", response)
  }
}

let updatingSettings = false

async function fetchSettings() {
  updatingSettings = true
  const response = await fetch(apiUrl("/settings"))
  if (response.ok) {
    $settings.set(await response.json())
  } else {
    await addError("Failed to fetch settings", response)
  }
  updatingSettings = false
}

async function updateSettings(pinChanged: boolean) {
  const settings = $settings.get()
  const pin = $pin.get()
  if (updatingSettings || !settings || (pin.valid === false && !pin.value)) {
    return
  }
  updatingSettings = true
  const response = await fetch(apiUrl("/settings"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...settings, pin: pin.value }),
  })
  if (response.ok) {
    $pin.set({ ...pin, valid: true })
  } else {
    if (response.status === 403) {
      $pin.set({ ...pin, valid: false })
      if (pinChanged && pin.value) {
        await addError("Invalid PIN. Please check your settings.")
        $activeTab.set("tab-settings")
      }
    } else {
      await addError("Failed to update settings", response)
    }
  }
  updatingSettings = false
}

async function fetchServerConfig() {
  const response = await fetch(apiUrl("/server-config"))
  if (response.ok) {
    $serverCfg.set(await response.json())
  } else {
    await addError("Failed to fetch server config", response)
  }
}

export async function togglePauseProcessing() {
  const { pauseProcessing } = $serverCfg.get()
  await fetch(apiUrl(pauseProcessing ? "/worker/resume" : "/worker/pause"), {
    method: "POST",
  })
  await fetchServerConfig()
}
