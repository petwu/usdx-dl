<script setup lang="ts">
import Logo from "#/logo.svg"
import AppSettings from "@/components/AppSettings.vue"
import QueueItem from "@/components/QueueItem.vue"
import ScrollContainer from "@/components/ScrollContainer.vue"
import SongCard from "@/components/SongCard.vue"
import ThemeSwitcher from "@/components/ThemeSwitcher.vue"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TabContent, TabList, Tabs, TabTrigger } from "@/components/ui/tabs"
import { ansiToHtml } from "@/lib/ansi"
import { apiUrl, websocketUrl } from "@/lib/host"
import { cn } from "@/lib/utils"
import { sref } from "@/lib/vue-utils"
import type { PipelineContext, ServerState, Settings, SongMetadata } from "@/types/api"
import {
  ChevronsLeftRightEllipsis,
  Pause,
  Play,
  SendHorizontal,
  Text,
  Trash2,
  TriangleAlert,
  Unplug,
  WrapText,
  X,
} from "@lucide/vue"
import { computed, onMounted, onUnmounted, ref, watch } from "vue"

// backend state
const songs = ref<(SongMetadata & { id: string })[]>([])
const songsIntervalHandle = ref<number | null>(null)
const state = ref<ServerState>({ processing: null, queue: [] })
const stateIntervalHandle = ref<number | null>(null)
const settings = ref<Settings | null>(null)
const settingsIntervalHandle = ref<number | null>(null)
const updatingSettings = ref(false)
const pinValue = sref<string>("settings:pin", "")
const pinValid = ref<boolean | undefined>(undefined)
const ws = ref<WebSocket | null>(null)
const logBuffer = ref<string[]>([])
const errors = ref<string[]>([])

// UI state
const mounted = ref(false)
const inputDisabled = ref<boolean>(false)
const link = ref<string>("")
const activeTab = sref<string>("tab:active", "tab-queue")
const songsFilter = sref<string>("songs:filter", "")
const wrapLog = sref<boolean>("switch:wrap-log", false)

const filteredSongs = computed(() => {
  if (!songsFilter.value) {
    return songs.value
  }
  const filter = songsFilter.value.toLowerCase()
  return songs.value.filter(
    (song) =>
      song.artist.toLowerCase().includes(filter) ||
      song.title.toLowerCase().includes(filter),
  )
})

watch(settings, () => updateSettings(false), { deep: true })
watch(pinValue, () => updateSettings(true), { deep: true })

async function addError(
  message: string,
  payload: Response | string | undefined = undefined,
) {
  let details: string | undefined = undefined
  if (!payload) {
  } else if (typeof payload === "string") {
    details = payload
  } else {
    if (payload.ok) {
      return
    }
    let details = payload.statusText
    const data = await payload.json()
    if (typeof data === "object" && "detail" in data) {
      if (typeof data.detail === "string") {
        details = data.detail
        if (/(usdb.+cookie|cookie.+usdb|PHPSESSID)/i.test(details)) {
          activeTab.value = "tab-settings"
        }
      } else if (Array.isArray(data.detail)) {
        details = data.detail
          .map((d: any) => {
            if (typeof d === "object" && d.type === "missing") {
              return `${d.msg} '${d.loc.join(".")}'`
            } else {
              return String(d)
            }
          })
          .join(", ")
      }
    }
  }
  if (details) {
    errors.value.push(`${message}: ${details}`)
  } else {
    errors.value.push(message)
  }
}

async function fetchSettings() {
  const response = await fetch(apiUrl("settings"))
  if (response.ok) {
    settings.value = await response.json()
  } else {
    await addError("Failed to fetch settings", response)
  }
}

async function fetchState() {
  const response = await fetch(apiUrl("state"))
  if (response.ok) {
    state.value = await response.json()
  } else {
    await addError("Failed to fetch state", response)
  }
}

async function fetchSongs() {
  const response = await fetch(apiUrl("songs"))
  if (response.ok) {
    songs.value = await response.json()
  } else {
    await addError("Failed to fetch songs", response)
  }
}

async function updateSettings(pinChanged: boolean) {
  if (
    updatingSettings.value ||
    !settings.value ||
    (pinValid.value === false && !pinValue.value)
  ) {
    return
  }
  updatingSettings.value = true
  const response = await fetch(apiUrl("settings"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...settings.value, pin: pinValue.value }),
  })
  if (response.ok) {
    pinValid.value = true
  } else {
    if (response.status === 403) {
      pinValid.value = false
      if (pinChanged && pinValue.value) {
        errors.value.push("Invalid PIN. Please check your settings.")
        activeTab.value = "tab-settings"
      }
    } else {
      await addError("Failed to update settings", response)
    }
  }
  updatingSettings.value = false
}

async function queueApiRequest(fetchPromise: Promise<Response>) {
  inputDisabled.value = true
  try {
    const response = await fetchPromise
    if (response.ok) {
      await fetchState()
    } else {
      await addError("Failed to update queue", response)
    }
  } finally {
    inputDisabled.value = false
  }
}

async function addToQueue() {
  if (!link.value) {
    return
  }
  await queueApiRequest(
    fetch(apiUrl("enqueue"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: link.value }),
    }),
  )
  link.value = ""
  activeTab.value = "tab-queue"
}

async function removeFromQueue(item: PipelineContext) {
  await queueApiRequest(
    fetch(apiUrl("dequeue"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
}

async function moveQueueItem(
  item: PipelineContext,
  direction: "up" | "down",
  toEnd: boolean,
) {
  await queueApiRequest(
    fetch(apiUrl("move"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item, direction, toEnd }),
    }),
  )
}

async function updateQueueItem(item: PipelineContext, done: () => void) {
  await queueApiRequest(
    fetch(apiUrl("update"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
  done()
}

async function retryQueueItem(item: PipelineContext) {
  await queueApiRequest(
    fetch(apiUrl("retry"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
}

async function clearLog() {
  logBuffer.value = []
  await queueApiRequest(fetch(apiUrl("clear-log"), { method: "DELETE" }))
}

function connectWebSocket() {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    return
  }
  logBuffer.value = []
  ws.value = new WebSocket(websocketUrl())
  ws.value.onmessage = (event) => {
    handleWebSocketMessage(event.data)
  }
  ws.value.onclose = () => {
    ws.value = null
  }
}

type WebSocketMessage = {
  type: string
  data: any
}

async function handleWebSocketMessage(msg: string) {
  if (!msg) return
  try {
    const { type, data }: WebSocketMessage = JSON.parse(msg)
    switch (type) {
      case "log":
        const logLine = ansiToHtml(data.text)
        if (logBuffer.value.length > 0 && data.override) {
          logBuffer.value[logBuffer.value.length - 1] = logLine
            .replace(/^\r+/, "")
            .replace(/\n+$/, "")
        } else {
          logBuffer.value.push(logLine)
        }
        while (logBuffer.value.length > 1000) {
          logBuffer.value.shift()
        }
        break
      case "error":
        addError(data)
        break
      default:
        addError(`Unknown WebSocket message type: ${type}`, data)
    }
  } catch (error) {
    addError("Failed to parse WebSocket message", msg)
  }
}

onMounted(() => {
  const pullIntervalSlow = import.meta.env.DEV ? 5000 : 10000
  const pullIntervalFast = import.meta.env.DEV ? 5000 : 1000
  connectWebSocket()
  fetchSettings()
  settingsIntervalHandle.value = setInterval(fetchSettings, pullIntervalSlow)
  fetchState()
  stateIntervalHandle.value = setInterval(fetchState, pullIntervalFast)
  fetchSongs()
  songsIntervalHandle.value = setInterval(fetchSongs, pullIntervalSlow)
  mounted.value = true
})
onUnmounted(() => {
  mounted.value = false
  if (stateIntervalHandle.value) {
    clearInterval(stateIntervalHandle.value)
  }
  if (songsIntervalHandle.value) {
    clearInterval(songsIntervalHandle.value)
  }
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<template>
  <header class="flex items-center justify-between gap-2 p-4">
    <img :src="Logo" alt="" class="size-9" />
    <span class="text-xl font-bold">usdx-dl</span>
    <ThemeSwitcher />
  </header>
  <main class="flex min-h-0 grow flex-col gap-2 p-4 pt-0">
    <div class="flex gap-2">
      <Input
        v-model="link"
        placeholder="https://usdb.animux.de/?link=detail&id=3715"
        :disabled="inputDisabled"
        @keyup.enter="addToQueue"
      />
      <Button
        size="icon"
        :disabled="!link || inputDisabled"
        title="add to queue"
        @click="addToQueue"
      >
        <SendHorizontal />
      </Button>
    </div>
    <div
      v-if="errors.length > 0"
      class="text-destructive border-destructive bg-destructive/10 rounded border"
    >
      <p
        class="bg-destructive text-destructive-foreground flex items-center gap-1 rounded-t-lg p-2 leading-0 font-bold"
      >
        <TriangleAlert :size="16" :stroke-width="2.5" />
        <span>{{ errors.length === 1 ? "Error" : `${errors.length} Errors` }}</span>
        <span class="grow"></span>
        <button @click="errors = []"><X :size="16" /></button>
      </p>
      <p v-if="errors.length === 1" class="p-2 text-sm">{{ errors[0] }}</p>
      <ol v-else class="max-h-32 list-inside list-decimal overflow-y-auto p-2 text-sm">
        <li v-for="error in errors">{{ error }}</li>
      </ol>
    </div>
    <div
      v-if="mounted && !ws"
      class="text-warning flex items-center justify-center gap-2 text-sm max-sm:justify-between"
    >
      <div class="flex items-center gap-2">
        <Unplug :size="16" />
        <span><span class="font-bold">Warning:</span> Connection closed.</span>
      </div>
      <Button size="sm" variant="warning" @click="connectWebSocket">
        <ChevronsLeftRightEllipsis />
        Reconnect
      </Button>
    </div>
    <Tabs v-model="activeTab" class="min-h-32 grow">
      <div class="flex items-center gap-2">
        <Button
          v-if="settings"
          size="icon"
          :variant="settings?.pauseProcessing ? 'warning' : 'outline'"
          title="pause/resume processing"
          @click="settings.pauseProcessing = !settings.pauseProcessing"
          :class="
            cn('size-9', settings?.pauseProcessing ? '' : 'bg-muted border-muted')
          "
        >
          <Play v-if="settings?.pauseProcessing" />
          <Pause v-else />
        </Button>
        <TabList class="w-full">
          <TabTrigger id="tab-queue">Queue</TabTrigger>
          <TabTrigger id="tab-songs">Songs</TabTrigger>
          <TabTrigger id="tab-output">Output</TabTrigger>
          <TabTrigger id="tab-settings">Settings</TabTrigger>
        </TabList>
      </div>
      <template v-if="activeTab === 'tab-queue' && settings?.pauseProcessing">
        <div
          class="bg-warning/10 text-warning border-warning flex items-start gap-2 rounded border p-2 text-sm"
        >
          <TriangleAlert :size="16" :stroke-width="2.5" class="mt-0.5" />
          <div>
            <p>Processing is paused ...</p>
            <p v-if="state.processing">(The current item will be finished.)</p>
          </div>
        </div>
      </template>
      <template v-if="activeTab === 'tab-songs'">
        <TabContent id="tab-songs" class="grow-0">
          <div class="flex items-center">
            <Input v-model="songsFilter" placeholder="Filter songs ..." />
            <span
              class="text-muted-foreground shrink-0 text-right text-sm tabular-nums"
              :style="{ minWidth: songs.length.toString().length * 2 + 2 + 'ch' }"
            >
              {{ filteredSongs.length }}/{{ songs.length }}
            </span>
          </div>
        </TabContent>
      </template>
      <TabContent id="tab-queue" class="min-h-0">
        <ScrollContainer direction="y" autoScroll="y" class="h-full">
          <TransitionGroup tag="ul" name="queue" class="relative block">
            <QueueItem
              v-if="state.processing"
              :item="state.processing"
              :isProcessing="true"
              @click-badge="activeTab = 'tab-output'"
            />
            <QueueItem
              v-for="(item, index) in state.queue"
              :key="item.uuid"
              as="li"
              :index="index"
              :size="state.queue.length"
              :item="item"
              :disabled="inputDisabled"
              class="not-first:mt-2"
              @remove="removeFromQueue"
              @move="moveQueueItem"
              @update="updateQueueItem"
              @retry="retryQueueItem"
            />
          </TransitionGroup>
        </ScrollContainer>
      </TabContent>
      <TabContent id="tab-songs" class="min-h-0">
        <ScrollContainer direction="y" class="h-full">
          <TransitionGroup
            tag="ul"
            name="songs"
            class="xs:grid-cols-[repeat(auto-fit,minmax(320px,1fr))] grid grid-cols-1 gap-2"
          >
            <SongCard
              as="li"
              v-for="song in filteredSongs"
              :key="JSON.stringify(song)"
              :song="song"
            />
          </TransitionGroup>
        </ScrollContainer>
      </TabContent>
      <TabContent id="tab-output" class="min-h-0">
        <div
          class="bg-card relative h-full overflow-auto rounded border font-mono text-xs"
        >
          <div role="group" class="absolute top-0 right-0 z-10">
            <button
              class="bg-card rounded-bl-lg border-b border-l px-3 py-2 disabled:cursor-not-allowed disabled:opacity-50"
              title="clear log"
              :disabled="logBuffer.length === 0"
              @click="clearLog()"
            >
              <Trash2 :size="16" />
            </button>
            <button
              class="bg-card border-b border-l px-3 py-2"
              title="wrap lines"
              @click="wrapLog = !wrapLog"
            >
              <Text v-if="wrapLog" :size="16" />
              <WrapText v-else :size="16" />
            </button>
          </div>
          <ScrollContainer direction="xy" autoScroll="y" class="h-full">
            <div
              :class="
                cn([
                  'p-4',
                  wrapLog
                    ? 'w-full wrap-break-word whitespace-pre-wrap'
                    : 'w-fit whitespace-pre',
                ])
              "
            >
              <p v-for="line in logBuffer" v-html="line" />
            </div>
          </ScrollContainer>
        </div>
      </TabContent>
      <TabContent id="tab-settings" class="min-h-0">
        <ScrollContainer direction="y" class="h-full">
          <AppSettings
            v-model:settings="settings"
            v-model:pin="pinValue"
            :pinValid="pinValid"
          />
        </ScrollContainer>
      </TabContent>
    </Tabs>
  </main>
</template>

<style>
#app {
  width: 100dvw;
  height: 100dvh;
  display: flex;
  flex-direction: column;
}
</style>

<style scoped>
/**
 * <TransitionGroup> transitions
 * https://vuejs.org/guide/built-ins/transition-group
 */
.queue-move,
.queue-enter-active,
.queue-leave-active {
  position: relative;
  transition: all 0.25s ease;
}
.queue-leave-active {
  position: absolute;
  width: 100%;
}
.queue-enter-from,
.queue-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.songs-move,
.songs-enter-active,
.songs-leave-active {
  position: relative;
  transition: all 0.25s ease;
}
.songs-enter-from,
.songs-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
