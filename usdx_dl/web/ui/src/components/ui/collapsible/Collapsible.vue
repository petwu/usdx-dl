<script setup lang="ts">
import { provide } from "vue"

const props = defineProps<{
  defaultOpen?: boolean
}>()

const open = defineModel<boolean>()
if (props.defaultOpen !== undefined) {
  open.value = props.defaultOpen
}

provide("collapsible", {
  open: open,
  toggle: () => (open.value = !open.value),
})
</script>

<template>
  <div class="w-full" v-bind="$attrs">
    <slot :open="open" />
  </div>
</template>
