<script setup lang="ts">
import { cn } from "@/lib/utils"
import { CircleIcon } from "@lucide/vue"
import { computed, inject, type HTMLAttributes, type Ref } from "vue"

const props = defineProps<{
  value: string
  id?: string
  disabled?: boolean
  class?: HTMLAttributes["class"]
}>()

const model = inject<Ref<string | undefined>>("radioGroupModel")!
const isChecked = computed(() => model.value === props.value)

function select() {
  if (!props.disabled) {
    model.value = props.value
  }
}
</script>

<template>
  <button
    :id="props.id"
    type="button"
    role="radio"
    :aria-checked="isChecked"
    :disabled="props.disabled"
    :data-state="isChecked ? 'checked' : 'unchecked'"
    :class="
      cn(
        'border-input text-primary focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 aspect-square size-4 shrink-0 rounded-full border shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-3 disabled:cursor-not-allowed disabled:opacity-50',
        props.class,
      )
    "
    @click="select"
  >
    <span v-if="isChecked" class="relative flex items-center justify-center">
      <CircleIcon
        class="fill-primary absolute top-1/2 left-1/2 size-2 -translate-x-1/2 -translate-y-1/2"
      />
    </span>
  </button>
</template>
