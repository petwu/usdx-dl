<script setup lang="ts">
import { TabList, TabTrigger } from "."

const props = defineProps<{
  id: string
  label?: string
}>()
</script>

<template>
  <TabList
    ><TabTrigger :id="props.id" data-state="active">
      <slot>{{ props.label }}</slot>
    </TabTrigger>
  </TabList>
</template>
