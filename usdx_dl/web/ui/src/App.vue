<script setup lang="ts">
import { Main, Setup } from "@/pages"
import { $activePage, $activeTab } from "@/store/nav"
import { $serverCfg } from "@/store/settings"
import { connectWebSocket, disconnectWebSocket } from "@/store/websocket"
import { AlertTriangle, LoaderCircle } from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { onMounted, onUnmounted } from "vue"

const page = useStore($activePage)

$serverCfg.subscribe((cfg) => {
  if (JSON.stringify(cfg) === "{}") {
    return
  }
  if (cfg.setupDone) {
    $activePage.set("page-main")
  } else {
    $activePage.set("page-setup")
    $activeTab.set("tab-instructions")
  }
})

onMounted(connectWebSocket)
onUnmounted(disconnectWebSocket)
</script>

<template>
  <div v-if="!page" class="flex h-full items-center justify-center">
    <LoaderCircle :size="48" :stroke-width="2.5" class="animate-spin" />
  </div>
  <Setup v-else-if="page === 'page-setup'" />
  <Main v-else-if="page === 'page-main'" />
  <div
    v-else-if="
      typeof page === 'string' &&
      // @ts-ignore
      page.length > 0
    "
    class="text-destructive prose flex h-full flex-col items-center justify-center gap-2 text-lg *:m-0!"
  >
    <AlertTriangle :size="48" :stroke-width="2.5" />
    <h1>Error</h1>
    <p>
      Unknown page: <code class="text-destructive">{{ page }}</code>
    </p>
  </div>
</template>

<style>
#app {
  width: 100dvw;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
