<template>
  <Button
    size="icon"
    variant="outline"
    title="toggle theme (light/dark/auto)"
    :class="cn(['', props.class])"
    @click="rotateColorMode"
  >
    <component :is="modes[store]" class="size-5" />
  </Button>
</template>

<script setup lang="ts">
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Moon, Sun, SunMoon } from "@lucide/vue"
import { onMounted, ref, type FunctionalComponent, type HTMLAttributes } from "vue"

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()

const lsKey = "color-mode" // same as in ThemeDetection.astro
const prefersDark = ref<boolean>(false)
const modesRotation = ref<string[]>([])
const store = ref<string>("auto")
const modes: Record<string, FunctionalComponent> = {
  light: Sun,
  dark: Moon,
  auto: SunMoon,
}

function applyColorMode() {
  if (
    localStorage[lsKey] === "dark" ||
    (!("color-mode" in localStorage) && prefersDark)
  ) {
    document.documentElement.classList.add("dark")
  } else {
    document.documentElement.classList.remove("dark")
  }
  store.value = localStorage[lsKey] || "auto"
}

function rotateColorMode() {
  let newColorMode =
    modesRotation.value[
      (modesRotation.value.indexOf(store.value) + 1) % modesRotation.value.length
    ]
  if (newColorMode === "auto") {
    localStorage.removeItem("color-mode")
  } else {
    localStorage[lsKey] = newColorMode
  }
  applyColorMode()
}

onMounted(() => {
  prefersDark.value = window.matchMedia("(prefers-color-scheme: dark)").matches
  modesRotation.value = prefersDark.value
    ? ["auto", "light", "dark"]
    : ["auto", "dark", "light"]
  applyColorMode()
})
</script>
