<script setup lang="ts">
import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "vue"
import { type ButtonVariants, buttonVariants } from "."

interface Props {
  as?: "button" | "a"
  id?: string
  variant?: ButtonVariants["variant"]
  size?: ButtonVariants["size"]
  class?: HTMLAttributes["class"]
  disabled?: boolean
  title?: HTMLAttributes["title"]
  href?: string
  download?: string
  onclick?: string | ((event: MouseEvent) => void)
}

const props = withDefaults(defineProps<Props>(), {
  as: "button",
})

if (props.as !== "a" && props.href) {
  console.warn("Button with href should have the `as='a'` property.")
}
</script>

<template>
  <component
    :is="props.as"
    data-slot="button"
    :data-variant="variant"
    :data-size="size"
    :id="props.id"
    :disabled="props.disabled"
    :class="cn(buttonVariants({ variant, size }), props.class)"
    :title="props.title"
    :href="props.href"
    :download="props.download"
    :onclick="props.onclick"
  >
    <slot />
  </component>
</template>
