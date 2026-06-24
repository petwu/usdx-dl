<script setup lang="ts">
import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "vue"
import type { BadgeVariants } from "."
import { badgeVariants } from "."

const props = withDefaults(
  defineProps<{
    as?: string
    variant?: BadgeVariants["variant"]
    pill?: boolean
    size?: BadgeVariants["size"]
    class?: HTMLAttributes["class"]
  }>(),
  { as: "span" },
)
</script>

<template>
  <component
    :is="props.as"
    data-slot="badge"
    :class="cn(badgeVariants({ variant, size, pill }), props.class)"
  >
    <slot />
  </component>
</template>
