<script setup lang="ts">
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { cn } from "@/lib/utils"
import { Moon, Sun, SunMoon } from "@lucide/vue"
import {
  onMounted,
  ref,
  useId,
  watch,
  type FunctionalComponent,
  type HTMLAttributes,
} from "vue"

const props = withDefaults(
  defineProps<{
    /**
     * If true, the "auto" theme option will be hidden.
     * @default false
     */
    noAuto?: boolean
    /**
     * If true, show the text of the current theme next to the icon.
     * @default false
     */
    withText?: boolean
    /**
     * If true, show a button for each them instead of a single cycle button.
     * Implies `withText`.
     * @default false
     */
    fancy?: boolean
    /**
     * Additional classes to apply to the button.
     * @default ""
     */
    class?: HTMLAttributes["class"]
  }>(),
  {
    noAuto: false,
    withText: false,
    fancy: false,
  },
)

const id = {
  light: useId(),
  dark: useId(),
  auto: useId(),
}
const lsKey = "color-mode"
const prefersDark = ref<boolean>(false)
const modesRotation = ref<string[]>([])
const store = ref<string>("auto")
const modes: Record<string, FunctionalComponent> = {
  light: Sun,
  dark: Moon,
  auto: SunMoon,
}

watch(store, setColorMode)

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

function setColorMode(mode: string) {
  if (mode === "auto") {
    localStorage.removeItem("color-mode")
  } else {
    localStorage[lsKey] = mode
  }
  applyColorMode()
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

function t(mode: string, short: boolean = false) {
  switch (mode) {
    case "light":
      return short ? "light" : "light theme"
    case "dark":
      return short ? "dark" : "dark theme"
    case "auto":
      return short ? "auto" : "follow system theme"
  }
}

onMounted(() => {
  prefersDark.value = window.matchMedia("(prefers-color-scheme: dark)").matches
  modesRotation.value = prefersDark.value
    ? ["auto", "light", "dark"]
    : ["auto", "dark", "light"]
  if (props.noAuto) {
    modesRotation.value = modesRotation.value.filter((mode) => mode !== "auto")
  }
  applyColorMode()
})
</script>

<template>
  <RadioGroup
    v-if="props.fancy"
    v-model="store"
    :class="
      cn(
        '@container flex w-full items-center gap-2',
        props.noAuto ? 'xs:max-w-80' : 'xs:max-w-120',
        props.class,
      )
    "
  >
    <label
      :for="id.light"
      :class="
        cn(
          'border-background shrink grow overflow-hidden rounded border-2 text-center',
          store === 'light' && 'border-primary',
        )
      "
    >
      <div
        class="flex w-full flex-col items-center justify-center gap-2 bg-white p-4 text-black"
      >
        <Sun class="inline size-8" />
        <div class="capitalize">{{ t("light", true) }}</div>
        <RadioGroupItem :id="id.light" value="light" class="border-ring" />
      </div>
    </label>
    <label
      :for="id.dark"
      :class="
        cn(
          'border-background shrink grow overflow-hidden rounded border-2 text-center',
          store === 'dark' && 'border-primary',
        )
      "
    >
      <div
        class="flex w-full flex-col items-center justify-center gap-2 bg-black p-4 text-white"
      >
        <Moon class="inline size-8" />
        <div class="capitalize">{{ t("dark", true) }}</div>
        <RadioGroupItem :id="id.dark" value="dark" class="border-ring" />
      </div>
    </label>
    <template v-if="!props.noAuto">
      <label
        :for="id.auto"
        :class="
          cn(
            'border-background shrink grow overflow-hidden rounded border-2 text-center',
            store === 'auto' && 'border-primary',
          )
        "
      >
        <div
          class="relative isolate flex w-full flex-col items-center justify-center gap-2 bg-white p-4 text-black"
        >
          <SunMoon class="inline size-8" />
          <div class="capitalize">{{ t("auto", true) }}</div>
          <RadioGroupItem :id="id.auto" value="auto" class="border-ring" />
          <svg
            class="absolute inset-0 h-full w-full mix-blend-difference"
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
          >
            <path d="M 0 0 L 1 0 L 0 1 Z" fill="white" />
          </svg>
        </div>
      </label>
    </template>
  </RadioGroup>
  <Button
    v-else
    :size="withText ? 'default' : 'icon'"
    variant="outline"
    title="toggle theme (light/dark/auto)"
    :class="cn(['', props.class])"
    @click="rotateColorMode"
  >
    <component :is="modes[store]" class="size-5" />
    <span v-if="withText" class="capitalize">{{ t(store) }}</span>
  </Button>
</template>
