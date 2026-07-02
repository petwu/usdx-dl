<script setup lang="ts">
import { Main, Setup } from "@/pages"
import { $activePage } from "@/store/nav"
import { connectWebSocket, disconnectWebSocket } from "@/store/websocket"
import { AlertTriangle } from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { onMounted, onUnmounted } from "vue"

const page = useStore($activePage)

onMounted(connectWebSocket)
onUnmounted(disconnectWebSocket)
</script>

<template>
  <Setup v-if="page === 'page-setup'" />
  <Main v-else-if="page === 'page-main'" />
  <div
    v-else
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
}
</style>
