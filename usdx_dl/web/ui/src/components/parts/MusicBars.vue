<script setup lang="ts">
import { cn } from "@/lib/utils"
import { onUnmounted, ref, useTemplateRef, watch, type HTMLAttributes } from "vue"

const props = withDefaults(
  defineProps<{
    playing?: boolean
    bars?: number
    speed?: number // ms base interval between height changes
    minHeight?: number
    class?: HTMLAttributes["class"]
    barClass?: HTMLAttributes["class"]
  }>(),
  {
    playing: true,
    bars: 5,
    speed: 150,
    minHeight: 2,
  },
)

const container = useTemplateRef("containerRef")

const rand = (min: number, max: number) =>
  Math.floor(Math.random() * (max - min + 1)) + min

const barHeights = ref<number[]>(
  Array.from({ length: props.bars }, () => props.minHeight),
)
const currentDelays = ref<number[]>(
  Array.from({ length: props.bars }, () => props.speed),
)

let intervals: ReturnType<typeof setInterval>[] = []

function startBar(index: number) {
  const tick = () => {
    const delay = rand(props.speed * 0.5, props.speed * 1.5)
    currentDelays.value[index] = delay
    const maxHeight = container.value?.offsetHeight || 16
    barHeights.value[index] = rand(props.minHeight, maxHeight)
    intervals[index] = setTimeout(tick, delay)
  }

  // stagger start
  intervals[index] = setTimeout(tick, rand(0, props.speed))
}

function stopBars() {
  intervals.forEach((t) => clearTimeout(t))
  intervals = []
  barHeights.value = Array.from({ length: props.bars }, () => props.minHeight)
}

function startBars() {
  stopBars()
  intervals = Array.from({ length: props.bars }, () => 0)
  for (let i = 0; i < props.bars; i++) startBar(i)
}

watch(
  () => props.playing,
  (val) => (val ? startBars() : stopBars()),
  { immediate: true },
)

watch(
  () => props.bars,
  (val) => {
    barHeights.value = Array.from({ length: val }, () => props.minHeight)
    currentDelays.value = Array.from({ length: val }, () => props.speed)
    if (props.playing) startBars()
  },
)

onUnmounted(stopBars)
</script>

<template>
  <div
    ref="containerRef"
    :class="cn('flex size-6 items-center justify-between', props.class)"
  >
    <span
      v-for="i in bars"
      :key="i"
      :class="cn('bg-primary rounded-full transition-all', props.barClass)"
      :style="{
        width: `${70 / bars}%`,
        height: playing ? `${barHeights[i - 1]}px` : '4px',
        transition: playing
          ? `height ${currentDelays[i - 1]}ms ease-in-out`
          : 'height 0.3s ease',
      }"
    />
  </div>
</template>
