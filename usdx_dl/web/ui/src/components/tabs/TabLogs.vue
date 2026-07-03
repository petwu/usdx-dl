<script setup lang="ts">
import ScrollContainer from "@/components/ScrollContainer.vue"
import { cn } from "@/lib/utils"
import { sref } from "@/lib/vue-utils"
import { $logBuffer, clearLog } from "@/store/logs"
import { Text, Trash2, WrapText } from "@lucide/vue"
import { useStore } from "@nanostores/vue"

const logBuffer = useStore($logBuffer)
const wrapLog = sref<boolean>("switch:wrap-log", false)
</script>

<template>
  <div class="bg-card relative h-full overflow-auto rounded border font-mono text-xs">
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
    <ScrollContainer direction="xy" autoScroll="y" class="h-full" gutter="0px">
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
        <p v-if="logBuffer.length > 0" v-for="line in logBuffer" v-html="line" />
        <p v-else class="text-muted-foreground italic">no log entries yet ...</p>
      </div>
    </ScrollContainer>
  </div>
</template>
