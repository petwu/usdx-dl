<script setup lang="ts">
import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "vue"
import type { ButtonGroupVariants } from "."

interface Props {
  class?: HTMLAttributes["class"]
  orientation?: ButtonGroupVariants["orientation"]
}

const props = withDefaults(defineProps<Props>(), {})
</script>

<template>
  <div
    role="group"
    :data-orientation="props.orientation"
    :class="
      cn(
        'bg-muted flex items-center gap-2 rounded-md border px-4 text-sm font-medium shadow-xs [&_svg]:pointer-events-none [&_svg:not([class*=\'size-\'])]:size-4',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
