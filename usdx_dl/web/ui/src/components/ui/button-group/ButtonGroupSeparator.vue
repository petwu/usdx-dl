<script setup lang="ts">
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "vue"

const props = withDefaults(
  defineProps<{
    orientation?: "horizontal" | "vertical"
    class?: HTMLAttributes["class"]
  }>(),
  {
    orientation: "vertical",
  },
)
</script>

<template>
  <Separator
    data-slot="button-group-separator"
    :orientation="props.orientation"
    :class="
      cn(
        'bg-input relative m-0! self-stretch data-[orientation=vertical]:h-auto',
        props.class,
      )
    "
  />
</template>
