<script setup lang="ts">
import { BorderBeam, QueueItem, QueueSkeleton } from "@/components/parts"
import ScrollContainer from "@/components/ScrollContainer.vue"
import TabLink from "@/components/ui/tabs/TabLink.vue"
import { $activeTab } from "@/store/nav"
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
import type { Ref } from "vue"

const state = useStore($state) as Ref<ServerState>
const progress = useStore($progress)
</script>

<template>
  <ScrollContainer direction="y" autoScroll="y" class="h-full">
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
    <TransitionGroup tag="ul" name="queue" class="relative block min-h-full">
      <BorderBeam
        v-if="state.processing"
        as="li"
        border-width="2px"
        class="border-primary/20 rounded"
      >
        <QueueItem
          :key="state.processing.uuid"
          :item="state.processing"
          :isProcessing="true"
          :progress="progress"
          @click-badge="$activeTab.set('tab-logs')"
        />
      </BorderBeam>
      <QueueSkeleton
        v-for="_ in state.pending ?? 0"
        as="li"
        :key="`pending-${_}`"
        class="not-first:mt-2"
      />
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
    </TransitionGroup>
  </ScrollContainer>
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
