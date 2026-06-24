<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch,
} from "vue"

type Direction = "x" | "y" | "xy" | "both"

const props = withDefaults(
  defineProps<{
    /** Scrollable direction(s). */
    direction?: Direction
    /** Whether to automatically scroll to the end of the content.
     * Can be restricted to only one axis even if the direction is "both". */
    autoScroll?: boolean | Direction
  }>(),
  {
    direction: "y",
    autoScroll: false,
  },
)

const containerRef = useTemplateRef("containerRef")
const isPaused = ref(false)

const isAtEnd = (): boolean => {
  const el = containerRef.value
  if (!el) return false

  const tolerance = 4 // px threshold to consider "at end"

  if (props.autoScroll === "x") {
    return el.scrollLeft + el.clientWidth >= el.scrollWidth - tolerance
  } else if (props.autoScroll === "y") {
    return el.scrollTop + el.clientHeight >= el.scrollHeight - tolerance
  } else {
    const atX = el.scrollLeft + el.clientWidth >= el.scrollWidth - tolerance
    const atY = el.scrollTop + el.clientHeight >= el.scrollHeight - tolerance
    return atX && atY
  }
}

const scrollToEnd = () => {
  const el = containerRef.value
  if (!el || !props.autoScroll) return

  if (props.autoScroll === "x") {
    el.scrollLeft = el.scrollWidth
  } else if (props.autoScroll === "y") {
    el.scrollTop = el.scrollHeight
  } else {
    el.scrollLeft = el.scrollWidth
    el.scrollTop = el.scrollHeight
  }
}

const handleScroll = () => {
  if (!props.autoScroll) return

  if (isAtEnd()) {
    isPaused.value = false
  } else {
    isPaused.value = true
  }
}

let observer: MutationObserver | null = null

const onMutation = () => {
  if (!props.autoScroll || isPaused.value) return
  nextTick(scrollToEnd)
}

onMounted(() => {
  const el = containerRef.value
  if (!el) return

  // MutationObserver watches for new content being added
  observer = new MutationObserver(onMutation)
  observer.observe(el, { childList: true, subtree: true, characterData: true })

  // initial scroll if autoScroll is already enabled
  if (props.autoScroll) {
    nextTick(scrollToEnd)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

// react to autoScroll prop toggling
watch(
  () => props.autoScroll,
  (val) => {
    if (val) {
      isPaused.value = false
      nextTick(scrollToEnd)
    }
  },
)

const overflowStyle = computed(() => {
  switch (props.direction) {
    case "x":
      return { overflowX: "auto", overflowY: "hidden" } as const
    case "y":
      return { overflowX: "hidden", overflowY: "auto" } as const
    default:
      return { overflow: "auto" } as const
  }
})
</script>

<template>
  <div ref="containerRef" :style="overflowStyle" @scroll.passive="handleScroll">
    <slot />
  </div>
</template>
