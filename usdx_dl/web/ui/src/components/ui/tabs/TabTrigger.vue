<script setup lang="ts">
import { cn } from "@/lib/utils"
import { computed, inject, type HTMLAttributes, type Ref } from "vue"

const props = defineProps<{
  id: string
  class?: HTMLAttributes["class"]
}>()

const activeTab = inject<Ref<string>>("activeTab")!
const setTab = inject<(id: string) => void>("setTab")!

const isActive = computed(() => activeTab.value === props.id)
</script>

<template>
  <button
    @click="setTab(id)"
    :data-state="isActive ? 'active' : 'inactive'"
    :class="
      cn(
        'data-[state=active]:bg-background dark:data-[state=active]:text-foreground focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:outline-ring dark:data-[state=active]:border-input dark:data-[state=active]:bg-input/30 text-foreground dark:text-muted-foreground inline-flex h-[calc(100%-1px)] flex-1 items-center justify-center gap-1.5 rounded-md border border-transparent px-2 py-1 text-sm font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:ring-3 focus-visible:outline-1 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:shadow-sm [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=\'size-\'])]:size-4',
        props.class,
      )
    "
  >
    <slot />
  </button>
</template>
