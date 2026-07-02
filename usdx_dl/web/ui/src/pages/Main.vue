<script setup lang="ts">
import Logo from "#/logo.svg"
import {
  TabInstructions,
  TabLogs,
  TabQueue,
  TabSettings,
  TabSongs,
} from "@/components/tabs"
import ThemeSwitcher from "@/components/ThemeSwitcher.vue"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TabContent, TabList, Tabs, TabTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { $errors } from "@/store/errors"
import { $activeTab } from "@/store/nav"
import { $settings, togglePauseProcessing } from "@/store/settings"
import { $state, addToQueue } from "@/store/state"
import { $ws, connectWebSocket } from "@/store/websocket"
import {
  ChevronsLeftRightEllipsis,
  HelpCircle,
  Pause,
  Play,
  SendHorizontal,
  TriangleAlert,
  Unplug,
  X,
} from "@lucide/vue"
import { useStore, useVModel } from "@nanostores/vue"
import { ref, type Ref } from "vue"

// global state
const errors = useStore($errors)
const settings = useStore($settings)
const state = useStore($state)
const activeTab = useVModel($activeTab) as Ref<string>

// backend state
const ws = useStore($ws)

// UI state
const inputDisabled = ref<boolean>(false)
const link = ref<string>("")
</script>

<template>
  <header
    v-if="settings && !settings.isWebview"
    class="flex items-center justify-between gap-2 p-2 pb-0"
  >
    <img :src="Logo" alt="" class="size-9" />
    <span class="text-xl font-bold">usdx-dl</span>
    <ThemeSwitcher />
  </header>
  <main class="flex min-h-0 grow flex-col gap-2 p-2">
    <div class="flex gap-2">
      <Input
        v-model="link"
        placeholder="https://usdb.animux.de/?link=detail&id=3715"
        :disabled="inputDisabled"
        @keyup.enter="addToQueue(link)"
      />
      <Button
        size="icon"
        :disabled="!link || inputDisabled"
        title="add to queue"
        @click="addToQueue(link)"
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
      v-if="ws === null"
      class="text-warning flex items-center justify-center gap-2 text-sm max-sm:justify-between"
    >
      <div class="flex items-center gap-2">
        <Unplug :size="16" />
        <span><span class="font-bold">Warning:</span> Connection closed.</span>
      </div>
      <Button size="sm" variant="warning" @click="connectWebSocket()">
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
            <TabTrigger id="tab-logs">Output</TabTrigger>
            <TabTrigger id="tab-settings">Settings</TabTrigger>
            <TabTrigger id="tab-instructions">
              <HelpCircle class="text-blue-500 sm:hidden" />
              <span class="max-sm:hidden">Instructions</span>
            </TabTrigger>
          </TabList>
        </div>
      </div>
      <template v-if="settings?.pauseProcessing">
        <div
          class="bg-warning/10 text-warning border-warning relative flex items-start gap-2 rounded border p-2 text-sm"
        >
          <div
            width="10"
            height="5"
            rounded="false"
            viewBox="0 0 12 6"
            preserveAspectRatio="none"
            :class="
              cn(
                'bg-warning size-2 rotate-45 rounded-[1px]',
                'absolute top-0 left-4.5 -translate-x-1/2 -translate-y-1/2',
                'mask-linear-135 mask-linear-from-50% mask-linear-to-50%',
              )
            "
            style="display: block"
          />
          <TriangleAlert :size="16" :stroke-width="2.5" class="mt-0.5" />
          <div>
            <p>Processing is paused ...</p>
            <p v-if="state.processing">(The current item will be finished.)</p>
          </div>
        </div>
      </template>
      <TabContent id="tab-queue" class="min-h-0">
        <TabQueue />
      </TabContent>
      <TabContent id="tab-songs" class="min-h-0">
        <TabSongs />
      </TabContent>
      <TabContent id="tab-logs" class="min-h-0">
        <TabLogs />
      </TabContent>
      <TabContent id="tab-settings" class="min-h-0">
        <TabSettings />
      </TabContent>
      <TabContent id="tab-instructions" class="min-h-0">
        <TabInstructions />
      </TabContent>
    </Tabs>
  </main>
</template>
