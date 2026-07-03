<script setup lang="ts">
import { TabList, TabTrigger } from "."

const props = defineProps<{
  id: string
  label?: string
  disabled?: boolean
}>()
</script>

<template>
  <TabList
    ><TabTrigger :id="props.id" :disabled="props.disabled" data-state="active">
      <slot>{{ props.label }}</slot>
    </TabTrigger>
  </TabList>
</template>
