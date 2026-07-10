<script setup lang="ts">
import { BorderBeam, QueueItem, QueueSkeleton } from "@/components/parts"
import ScrollContainer from "@/components/ScrollContainer.vue"
import TabLink from "@/components/ui/tabs/TabLink.vue"
import { $activeTab } from "@/store/nav"
import { cancelWorker } from "@/store/settings"
import {
  $progress,
  $state,
  moveQueueItem,
  removeFromQueue,
  retryQueueItem,
  updateQueueItem,
} from "@/store/state"
import type { ServerState } from "@/types/api"
import { HelpCircle, ListMusic } from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { onMounted, onUnmounted, ref, useTemplateRef, type Ref } from "vue"

const state = useStore($state) as Ref<ServerState>
const progress = useStore($progress)

const pinProcessingItem = ref(true)
const pinnedItemRef = useTemplateRef("pinnedItemRef")

function onResize() {
  pinProcessingItem.value = window.innerHeight >= 480
}

onMounted(() => {
  onResize()
  window.addEventListener("resize", onResize)
})
onUnmounted(() => {
  window.removeEventListener("resize", onResize)
})
</script>

<template>
  <div class="flex h-full flex-col">
    <div ref="pinnedItemRef"></div>
    <div
      v-if="!state.processing && !state.queue.length && !state.pending"
      class="absolute top-1/2 left-1/2 z-10 flex w-fit -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 text-center"
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
    <ScrollContainer v-else direction="y" autoScroll="y" class="min-h-0 shrink grow">
      <TransitionGroup tag="ul" name="queue" class="relative block min-h-full">
        <Teleport
          v-if="state.processing"
          :to="pinnedItemRef"
          :disabled="!pinProcessingItem"
          defer
        >
          <BorderBeam
            as="li"
            :key="state.processing.uuid"
            border-width="2px"
            class="border-primary/20 rounded"
          >
            <QueueItem
              :item="state.processing"
              :isProcessing="true"
              :progress="progress"
              @click-badge="$activeTab.set('tab-logs')"
              @cancel="cancelWorker"
            />
          </BorderBeam>
          <hr v-if="pinProcessingItem" class="border-primary/20 my-2" />
        </Teleport>
        <QueueItem
          v-for="(item, index) in state.queue"
          :key="item.uuid"
          as="li"
          :index="index"
          :size="state.queue.length"
          :item="item"
          class="not-first:mt-2"
          @remove="removeFromQueue"
          @move="moveQueueItem"
          @update="updateQueueItem"
          @retry="retryQueueItem"
        />
        <QueueSkeleton
          v-for="_ in state.pending ?? 0"
          as="li"
          :key="`pending-${_}`"
          class="not-first:mt-2"
        />
      </TransitionGroup>
    </ScrollContainer>
  </div>
</template>

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
  animation: none;
}
.queue-enter-from,
.queue-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
