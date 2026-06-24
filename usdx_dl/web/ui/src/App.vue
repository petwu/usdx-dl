<script setup lang="ts">
import Logo from "#/logo.svg"
import QueueItem from "@/components/QueueItem.vue"
import ScrollContainer from "@/components/ScrollContainer.vue"
import SongCard from "@/components/SongCard.vue"
import ThemeSwitcher from "@/components/ThemeSwitcher.vue"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup } from "@/components/ui/radio-group"
import RadioGroupItem from "@/components/ui/radio-group/RadioGroupItem.vue"
import { Switch } from "@/components/ui/switch"
import { TabContent, TabList, Tabs, TabTrigger } from "@/components/ui/tabs"
import { ansiToHtml } from "@/lib/ansi"
import { apiUrl, websocketUrl } from "@/lib/host"
import { cn } from "@/lib/utils"
import { sref } from "@/lib/vue-utils"
import type { PipelineContext, ServerState, Settings, SongMetadata } from "@/types/api"
import {
  ChevronsLeftRightEllipsis,
  Info,
  Pause,
  Play,
  SendHorizontal,
  Text,
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
const ws = ref<WebSocket | null>(null)
const logBuffer = ref<string[]>([])
const errors = ref<string[]>([])

// UI state
const mounted = ref(false)
const inputDisabled = ref<boolean>(false)
const link = ref<string>("https://usdb.animux.de/?link=detail&id=1234") // TODO
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

watch(() => settings.value, updateSettings, { deep: true })

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
  const response = await fetch(`${apiUrl()}/settings`)
  if (response.ok) {
    settings.value = await response.json()
  } else {
    await addError("Failed to fetch settings", response)
  }
}

async function fetchState() {
  const response = await fetch(`${apiUrl()}/state`)
  if (response.ok) {
    state.value = await response.json()
  } else {
    await addError("Failed to fetch state", response)
  }
}

async function fetchSongs() {
  const response = await fetch(`${apiUrl()}/songs`)
  if (response.ok) {
    songs.value = await response.json()
  } else {
    await addError("Failed to fetch songs", response)
  }
}

async function updateSettings(newSettings: Settings | null) {
  if (!newSettings) {
    return
  }
  const response = await fetch(`${apiUrl()}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(newSettings),
  })
  if (!response.ok) {
    await addError("Failed to update settings", response)
  }
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
    fetch(`${apiUrl()}/enqueue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: link.value }),
    }),
  )
  // link.value = ""  // TODO
  activeTab.value = "tab-queue"
}

async function removeFromQueue(item: PipelineContext) {
  await queueApiRequest(
    fetch(`${apiUrl()}/dequeue`, {
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
    fetch(`${apiUrl()}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item, direction, toEnd }),
    }),
  )
}

async function updateQueueItem(item: PipelineContext, done: () => void) {
  await queueApiRequest(
    fetch(`${apiUrl()}/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
  done()
}

async function retryQueueItem(item: PipelineContext) {
  await queueApiRequest(
    fetch(`${apiUrl}/retry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item),
    }),
  )
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
          logBuffer.value[logBuffer.value.length - 1] = logLine.replace(/^\r+/, "")
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
        <li v-for="(error, index) in errors" :key="index">{{ error }}</li>
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
          title="pause/resume processing"
          @click="settings.pauseProcessing = !settings.pauseProcessing"
          class="size-8"
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
            <p v-if="state.processing">
              (The currently processing item will be finished.)
            </p>
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
          <ul class="flex flex-col gap-2">
            <QueueItem
              v-if="state.processing"
              :item="state.processing"
              :isProcessing="true"
              @click="activeTab = 'tab-output'"
            />
            <QueueItem
              v-for="(item, index) in state.queue"
              as="li"
              :index="index"
              :size="state.queue.length"
              :item="item"
              :disabled="inputDisabled"
              @remove="removeFromQueue"
              @move="moveQueueItem"
              @update="updateQueueItem"
              @retry="retryQueueItem"
            />
          </ul>
        </ScrollContainer>
      </TabContent>
      <TabContent id="tab-songs" class="min-h-0">
        <ScrollContainer direction="y" class="h-full">
          <ul
            class="xs:grid-cols-[repeat(auto-fit,minmax(320px,1fr))] grid grid-cols-1 gap-2"
          >
            <SongCard
              as="li"
              v-for="song in filteredSongs"
              :key="JSON.stringify(song)"
              :song="song"
            />
          </ul>
        </ScrollContainer>
      </TabContent>
      <TabContent id="tab-output" class="min-h-0">
        <div
          class="bg-card relative h-full overflow-auto rounded border font-mono text-xs"
        >
          <button
            :class="
              cn([
                'absolute top-0 right-0',
                'bg-card rounded-bl-lg border-b border-l px-3 py-2',
              ])
            "
            title="wrap lines"
            @click="wrapLog = !wrapLog"
          >
            <Text v-if="wrapLog" :size="16" />
            <WrapText v-else :size="16" />
          </button>
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
              <p v-for="(line, index) in logBuffer" :key="index" v-html="line" />
            </div>
          </ScrollContainer>
        </div>
      </TabContent>
      <TabContent id="tab-settings" class="min-h-0">
        <ScrollContainer direction="y" class="h-full">
          <div class="bg-card flex flex-col gap-4 rounded border p-4">
            <h3 class="text-lg font-bold">Download Options</h3>
            <div v-if="settings" class="grid grid-cols-[auto_1fr] items-center gap-2">
              <Label for="input:settings:usdb-cookie">USDB Cookie</Label>
              <Input
                v-model="settings.usdbCookie"
                id="input:settings:usdb-cookie"
                placeholder="PHPSESSID=..."
              />
              <details
                class="text-muted-foreground col-span-2 -mt-2 text-sm"
                :open="false"
              >
                <summary class="cursor-pointer">
                  How to get the PHPSESSID cookie?
                </summary>
                <ol class="list-outside list-decimal pl-4">
                  <li>
                    Go to
                    <a
                      href="https://usdb.animux.de"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      https://usdb.animux.de </a
                    >.
                  </li>
                  <li>Login to your account.</li>
                  <li>Open the browser's developer tools (F12).</li>
                  <li>
                    Run the following command in the console:
                    <pre class="bg-muted mt-1 rounded p-2 text-sm whitespace-pre-wrap">
(await cookieStore.get("PHPSESSID")).value</pre
                    >
                  </li>
                  <li>Copy the value and paste it into the above field.</li>
                </ol>
              </details>
            </div>
            <div v-if="settings" class="grid grid-cols-[auto_1fr] items-center gap-2">
              <Switch v-model="settings.noVideo" id="switch:settings:no-video" />
              <Label for="switch:settings:no-video">
                no video
                <span class="text-muted-foreground text-sm">[faster, less data]</span>
              </Label>
              <Switch v-model="settings.noLyrics" id="switch:settings:no-lyrics" />
              <Label for="switch:settings:no-lyrics">
                no lyrics
                <span class="text-muted-foreground text-sm">[less accurate]</span>
              </Label>
            </div>
            <hr />
            <h3 class="text-lg font-bold">AI Models</h3>
            <div v-if="settings">
              <h4 class="flex items-center gap-3">
                Stem Separation Model
                <a
                  href="https://github.com/nomadkaraoke/python-audio-separator"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-500 hover:underline"
                >
                  <Info :size="16" />
                </a>
              </h4>
              <RadioGroup v-model="settings.stemModel" class="items-start">
                <RadioGroupItem
                  id="radio:stem-model:demucs"
                  value="demucs"
                  class="mt-0.5"
                />
                <Label for="radio:stem-model:demucs" class="block">
                  Demucs
                  <span class="text-muted-foreground text-sm">(recommended)</span>
                </Label>
                <RadioGroupItem
                  id="radio:stem-model:mel-roformer"
                  value="mel-roformer"
                  class="mt-0.5"
                />
                <Label for="radio:stem-model:mel-roformer" class="block">
                  Mel-Band Roformer
                  <span class="text-muted-foreground text-sm">
                    [better, slow on CPU]
                  </span>
                </Label>
              </RadioGroup>
              <h4 class="flex items-center gap-3">
                Transcription Model (WhisperX)
                <a
                  href="https://github.com/openai/whisper/discussions/2363"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-500 hover:underline"
                >
                  <Info :size="16" />
                </a>
              </h4>
              <RadioGroup v-model="settings.whisperModel" class="items-start">
                <RadioGroupItem
                  id="radio:whisper-model:turbo"
                  value="turbo"
                  class="mt-0.5"
                />
                <Label for="radio:whisper-model:turbo" class="block">
                  turbo
                  <span class="text-muted-foreground text-sm">
                    (recommended) [fast, high quality]
                  </span>
                </Label>
                <RadioGroupItem
                  id="radio:whisper-model:large"
                  value="large"
                  class="mt-0.5"
                />
                <Label for="radio:whisper-model:large" class="block">
                  large
                  <span class="text-muted-foreground text-sm"
                    >[slow, highest quality]</span
                  >
                </Label>
                <RadioGroupItem
                  id="radio:whisper-model:medium"
                  value="medium"
                  class="mt-0.5"
                />
                <Label for="radio:whisper-model:medium" class="block">medium</Label>
                <RadioGroupItem
                  id="radio:whisper-model:small"
                  value="small"
                  class="mt-0.5"
                />
                <Label for="radio:whisper-model:small" class="block">small</Label>
                <RadioGroupItem
                  id="radio:whisper-model:base"
                  value="base"
                  class="mt-0.5"
                />
                <Label for="radio:whisper-model:base" class="block">base</Label>
                <RadioGroupItem
                  id="radio:whisper-model:tiny"
                  value="tiny"
                  class="mt-0.5"
                />
                <Label for="radio:whisper-model:tiny" class="block">
                  tiny
                  <span class="text-muted-foreground text-sm">[fast, low quality]</span>
                </Label>
              </RadioGroup>
            </div>
          </div>
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
