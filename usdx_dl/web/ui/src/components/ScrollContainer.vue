<script setup lang="ts">
import { cn } from "@/lib/utils"
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch,
  type HTMLAttributes,
} from "vue"

type Direction = "x" | "y" | "xy" | "both"

const props = withDefaults(
  defineProps<{
    /** Scrollable direction(s). */
    direction?: Direction
    /** Whether to automatically scroll to the end of the content.
     * Can be restricted to only one axis even if the direction is "both". */
    autoScroll?: boolean | Direction
    /** Whether to automatically scroll to the end of the content on initial render. */
    autoScrollOnMount?: boolean
    /** Padding to apply to the opposite axis of the scroll direction, to prevent e.g.
     * ring-* from being cut off. */
    gutter?: `${number}px` | `${number}rem` | `${number}em` | `${number}%`
    /** Additional classes to apply to the scroll container. */
    class?: HTMLAttributes["class"]
  }>(),
  {
    direction: "y",
    autoScroll: false,
    autoScrollOnMount: false,
    gutter: "4px",
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
  if (props.autoScroll && props.autoScrollOnMount) {
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
      return {
        overflowX: "auto",
        overflowY: "hidden",
        // overflow quirk: if one axis is auto/scroll/hidden, the other axis cannot be visible
        // give the container some room for e.g. ring-* and compensate with negative margin
        paddingBlock: props.gutter,
        marginBlock: `-${props.gutter}`,
      } as const
    case "y":
      return {
        overflowX: "hidden",
        overflowY: "auto",
        paddingInline: props.gutter,
        marginInline: `-${props.gutter}`,
      } as const
    default:
      return {
        overflow: "auto",
        padding: props.gutter,
        margin: `-${props.gutter}`,
      } as const
  }
})
</script>

<template>
  <div
    ref="containerRef"
    :style="overflowStyle"
    :class="
      cn(
        'scrollbar-thumb-foreground/50 scrollbar-thin scrollbar-track-transparent',
        props.class,
      )
    "
    @scroll.passive="handleScroll"
  >
    <slot />
  </div>
</template>
