<script setup lang="ts">
import Logo from "#/logo.svg"
import AppInstructions from "@/components/AppInstructions.vue"
import AppSettings from "@/components/AppSettings.vue"
import QueueItem from "@/components/QueueItem.vue"
import ScrollContainer from "@/components/ScrollContainer.vue"
import SongCard from "@/components/SongCard.vue"
import ThemeSwitcher from "@/components/ThemeSwitcher.vue"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TabContent, TabLink, TabList, Tabs, TabTrigger } from "@/components/ui/tabs"
import { ansiToHtml } from "@/lib/ansi"
import { apiUrl, websocketUrl } from "@/lib/host"
import { cn } from "@/lib/utils"
import { sref } from "@/lib/vue-utils"
import type {
  PipelineContext,
  ServerState,
  Settings,
  SongMetadata,
  Tool,
} from "@/types/api"
import {
  AlertTriangle,
  ChevronsLeftRightEllipsis,
  Download,
  File,
  FileTerminal,
  Globe2,
  HelpCircle,
  ListMusic,
  LoaderCircle,
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
const tools = ref<Tool[]>([])
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
const downloadingTools = ref<boolean>(false)
const link = ref<string>("")
const activeTab = sref<string>("tab:active", "tab-instructions", { noWatch: true })
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

async function fetchTools() {
  const response = await fetch(apiUrl("tools"))
  if (response.ok) {
    tools.value = await response.json()
  } else {
    await addError("Failed to fetch tools", response)
  }
}

async function autoDownloadTools() {
  downloadingTools.value = true
  inputDisabled.value = true
  const response = await fetch(apiUrl("tools/download"), { method: "POST" })
  if (response.ok) {
    await fetchTools()
  } else {
    await addError("Failed to auto-download tools", response)
  }
  inputDisabled.value = false
  downloadingTools.value = false
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

async function togglePauseProcessing() {
  inputDisabled.value = true
  await fetch(apiUrl("pause"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value: !settings.value?.pauseProcessing }),
  })
  await fetchSettings()
  inputDisabled.value = false
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

async function openSongFolder(id: string) {
  fetch(apiUrl("open-folder"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  })
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

onMounted(async () => {
  const pullIntervalSlow = import.meta.env.DEV ? 5000 : 10000
  const pullIntervalFast = import.meta.env.DEV ? 5000 : 1000
  await fetchTools()
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
  <template v-if="tools?.length > 0 && tools.some((tool) => !tool.version)">
    <main class="bg-destructive/10 flex h-dvh w-dvw items-center justify-center p-4">
      <div
        class="prose border-destructive bg-background flex h-fit max-h-full flex-col rounded border p-4"
      >
        <h2 class="text-destructive">
          <AlertTriangle class="-mt-1 mr-1 inline-block" />
          Missing Required Tools
        </h2>
        <div class="min-h-16 shrink grow overflow-y-auto">
          <p>
            The following required tools are missing. Please install them to continue.
            You can find installation instructions for each tool at the provided URL.
          </p>
          <p>
            If you have already installed the required tools, please make sure they are
            available in your system's <code>PATH</code> and restart the application.
          </p>
          <div v-for="tool in tools" class="my-8 flex gap-2">
            <div>
              <FileTerminal
                :class="
                  cn('size-4', tool.version ? 'text-success' : 'text-destructive')
                "
              />
            </div>
            <div>
              <div class="leading-none">
                <strong :class="cn(tool.version ? 'text-success' : 'text-destructive')">
                  {{ tool.name }}
                </strong>
                <span v-if="tool.version"> &nbsp; @{{ tool.version }}</span>
                <span v-else> &nbsp; (missing)</span>
              </div>
              <div class="*:text-muted-foreground mt-2 flex flex-col gap-2 text-sm">
                <a :href="tool.homepage" target="_blank" rel="noopener noreferrer">
                  <Globe2 class="-mt-1 inline size-4" /> Homepage
                </a>
                <a :href="tool.downloadUrl" target="_blank" rel="noopener noreferrer">
                  <Download class="-mt-1 inline size-4" /> Download (v{{ tool.latest }})
                </a>
                <span v-if="tool.version">
                  <File class="-mt-1 inline size-4" /> {{ tool.path }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <Button
          class="mt-8 w-full"
          :disabled="downloadingTools"
          @click="autoDownloadTools"
        >
          <Download v-if="!downloadingTools" />
          <LoaderCircle v-else class="animate-spin" />
          &nbsp; Auto-download all tools
        </Button>
      </div>
    </main>
  </template>
  <template v-else>
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
        <ol
          v-else
          class="max-h-32 list-inside list-decimal overflow-y-auto p-2 text-sm"
        >
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
      <Tabs
        v-model="activeTab"
        class="min-h-32 grow"
        history
        titleTemplate="usdx-dl - {tab}"
      >
        <div class="flex items-center gap-2">
          <Button
            v-if="settings"
            size="icon"
            :variant="settings?.pauseProcessing ? 'warning' : 'outline'"
            title="pause/resume processing"
            @click="togglePauseProcessing()"
            :class="
              cn('size-9', settings?.pauseProcessing ? '' : 'bg-muted border-muted')
            "
          >
            <Play v-if="settings?.pauseProcessing" />
            <Pause v-else />
          </Button>
          <div class="min-w-0 shrink grow overflow-x-auto whitespace-nowrap">
            <TabList class="flex w-full min-w-fit">
              <TabTrigger id="tab-queue">Queue</TabTrigger>
              <TabTrigger id="tab-songs">Songs</TabTrigger>
              <TabTrigger id="tab-output">Output</TabTrigger>
              <TabTrigger id="tab-settings">Settings</TabTrigger>
              <TabTrigger id="tab-instructions">
                <HelpCircle class="text-blue-500 sm:hidden" />
                <span class="max-sm:hidden">Instructions</span>
              </TabTrigger>
            </TabList>
          </div>
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
            <TransitionGroup tag="ul" name="queue" class="relative block min-h-full">
              <div
                v-if="!state.processing && !state.queue.length"
                class="absolute top-1/2 left-1/2 flex w-fit -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 text-center"
              >
                <p class="text-muted-foreground italic">Queue is empty.</p>
                <hr class="my-16 w-1/2" />
                <p>Need help?</p>
                <TabLink id="tab-instructions" class="w-full">
                  <HelpCircle class="text-blue-500" />
                  View Instructions
                </TabLink>
                <TabLink id="tab-songs" class="w-full">
                  <ListMusic class="text-fuchsia-500" />
                  Browse Songs
                </TabLink>
              </div>
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
                @open-folder="openSongFolder"
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
                <p
                  v-if="logBuffer.length > 0"
                  v-for="line in logBuffer"
                  v-html="line"
                />
                <p v-else class="text-muted-foreground italic">
                  no log entries yet ...
                </p>
              </div>
            </ScrollContainer>
          </div>
        </TabContent>
        <TabContent id="tab-settings" class="min-h-0">
          <ScrollContainer direction="y" class="h-full">
            <AppSettings
              v-model:settings="settings"
              v-model:pin="pinValue"
              v-model:tools="tools"
              :pinValid="pinValid"
            />
          </ScrollContainer>
        </TabContent>
        <TabContent id="tab-instructions" class="min-h-0">
          <ScrollContainer direction="y" class="h-full">
            <AppInstructions />
          </ScrollContainer>
        </TabContent>
      </Tabs>
    </main>
  </template>
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
