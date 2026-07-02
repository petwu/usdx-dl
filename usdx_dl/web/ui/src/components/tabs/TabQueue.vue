<script setup lang="ts">
import QueueItem from "@/components/QueueItem.vue"
import ScrollContainer from "@/components/ScrollContainer.vue"
import TabLink from "@/components/ui/tabs/TabLink.vue"
import { $activeTab } from "@/store/nav"
import {
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
</script>

<template>
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
        @click-badge="$activeTab.set('tab-logs')"
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
