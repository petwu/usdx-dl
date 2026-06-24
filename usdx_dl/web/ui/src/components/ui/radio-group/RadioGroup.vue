<script setup lang="ts">
import { cn } from "@/lib/utils"
import { provide, type HTMLAttributes } from "vue"

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()

const model = defineModel<string | undefined>({ required: true })
provide("radioGroupModel", model)
</script>

<template>
  <div
    role="radiogroup"
    :class="cn('my-2 grid grid-cols-[auto_1fr] items-center gap-2', props.class)"
  >
    <slot />
  </div>
</template>
