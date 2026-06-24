<script setup lang="ts">
import { cn } from "@/lib/utils"
import { computed, inject, type HTMLAttributes, type Ref } from "vue"

const props = defineProps<{
  id: string
  class?: HTMLAttributes["class"]
}>()

const activeTab = inject<Ref<string>>("activeTab")!
const isActive = computed(() => activeTab.value === props.id)
</script>

<template>
  <div v-if="isActive" :class="cn('flex-1 outline-none', props.class)">
    <slot />
  </div>
</template>
