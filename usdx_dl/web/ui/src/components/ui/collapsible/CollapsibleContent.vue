<script setup lang="ts">
import { inject, type Ref } from "vue"

const props = withDefaults(defineProps<{ as?: string }>(), { as: "div" })

const { open } = inject<{
  open: Ref<boolean>
  toggle: () => void
}>("collapsible")!
</script>

<template>
  <component :is="props.as" v-show="open">
    <slot />
  </component>
</template>
