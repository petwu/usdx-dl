<script setup lang="ts">
import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "vue"

const props = withDefaults(
  defineProps<{
    orientation?: "horizontal" | "vertical"
    class?: HTMLAttributes["class"]
  }>(),
  {
    orientation: "horizontal",
    decorative: true,
  },
)
</script>

<template>
  <div
    :class="
      cn(
        'bg-border shrink-0',
        props.orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        props.class,
      )
    "
  />
</template>
