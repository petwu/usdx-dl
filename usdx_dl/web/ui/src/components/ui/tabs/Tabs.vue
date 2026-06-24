<script setup lang="ts">
import { cn } from "@/lib/utils"
import { provide, type HTMLAttributes } from "vue"

const props = defineProps<{
  defaultTab?: string
  class?: HTMLAttributes["class"]
}>()

const activeTab = defineModel<string>({ default: "" })
if (!activeTab.value && props.defaultTab) {
  activeTab.value = props.defaultTab
}

function setTab(id: string) {
  activeTab.value = id
}

provide("activeTab", activeTab)
provide("setTab", setTab)
</script>

<template>
  <div :class="cn('flex flex-col gap-2', props.class)">
    <slot />
  </div>
</template>
