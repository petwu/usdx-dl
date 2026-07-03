<script setup lang="ts">
import Logo from "#/logo.svg"
import DownloadTools from "@/components/DownloadTools.vue"
import ScrollContainer from "@/components/ScrollContainer.vue"
import SongsFolder from "@/components/SongsFolder.vue"
import { Button } from "@/components/ui/button"
import { TabLink, Tabs } from "@/components/ui/tabs"
import UsdbCookie from "@/components/UsdbCookie.vue"
import { cn } from "@/lib/utils"
import { $settings, $setup, setupComplete } from "@/store/settings"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Cookie,
  Folder,
  Music,
  Wrench,
} from "@lucide/vue"
import { useStore, useVModel } from "@nanostores/vue"
import { computed, onMounted, onUnmounted, ref } from "vue"

const setup = useStore($setup)
const { usdbCookieModel } = useVModel($settings, ["usdbCookie"])
const numSteps = 5
const currentStep = ref<number>(0)
const stepDirection = ref<"forward" | "backward">("forward")

const canContinue = computed(() => {
  switch (currentStep.value) {
    case 0: // welcome
      return true
    case 1: // songs folder
      return setup.value.songsFolder
    case 2: // usdb cookie
      return setup.value.usdbCookie
    case 3: // download tools
      return setup.value.downloadTools
    case 4: // done
      return true
    default:
      return false
  }
})

function nextStep() {
  stepDirection.value = "forward"
  currentStep.value = Math.min(currentStep.value + 1, numSteps - 1)
}

function prevStep() {
  stepDirection.value = "backward"
  currentStep.value = Math.max(currentStep.value - 1, 0)
}

function jumpToStep(step: number) {
  stepDirection.value = step > currentStep.value ? "forward" : "backward"
  currentStep.value = Math.max(0, Math.min(step, numSteps - 1))
}

function kbdHandler(event: KeyboardEvent) {
  switch (event.key) {
    case "ArrowRight":
    case "Enter":
      if (canContinue.value) {
        if (currentStep.value < numSteps - 1) {
          nextStep()
        } else {
          setupComplete()
        }
      }
      break
    case "ArrowLeft":
    case "Escape":
      prevStep()
      break
  }
}

onMounted(() => {
  window.addEventListener("keydown", kbdHandler)
})
onUnmounted(() => {
  window.removeEventListener("keydown", kbdHandler)
})
</script>

<template>
  <header class="container flex items-center justify-center gap-4 p-4">
    <img :src="Logo" alt="" class="size-16" />
    <h1 class="text-xl font-bold">
      <span class="text-primary">usdx-dl</span><br />
      Setup Wizard
    </h1>
  </header>

  <main class="container flex min-h-0 grow flex-col gap-2 px-4">
    <nav>
      <div
        class="relative mx-auto my-4 flex h-8 w-full shrink-0 items-center justify-between"
      >
        <div
          class="absolute top-1/2 -z-10 h-1 w-full -translate-y-1/2 bg-gray-300/50"
        ></div>
        <div
          class="bg-primary absolute top-1/2 -z-10 h-1 -translate-y-1/2 transition-all duration-300 ease-in-out"
          :style="{ width: `${Math.min(currentStep / (numSteps - 1), 1) * 100}%` }"
        ></div>
        <div
          v-for="(_, i) in numSteps"
          :key="i"
          :class="
            cn(
              'size-8 cursor-pointer rounded-full shadow',
              'flex items-center justify-center',
              'transition-all duration-300 ease-in-out',
              '[&_svg]:size-4 [&_svg]:opacity-50 [&_svg]:transition-all [&_svg]:duration-300 [&_svg]:ease-in-out',
              currentStep >= i && '[&_svg]:opacity-100',
              currentStep >= i
                ? 'bg-primary text-primary-foreground'
                : 'bg-gray-300 text-gray-600',
              currentStep === i && 'scale-125',
            )
          "
          @click="jumpToStep(i)"
        >
          <Music v-if="i === 0" />
          <Folder v-else-if="i === 1" />
          <Cookie v-else-if="i === 2" />
          <Wrench v-else-if="i === 3" />
          <Check v-else-if="i === 4" />
        </div>
      </div>
    </nav>

    <TransitionGroup
      tag="div"
      name="setup"
      :class="
        cn(
          'prose relative block min-h-0 max-w-none shrink grow',
          `setup-${stepDirection}`,
        )
      "
    >
      <!-- step: welcome -->
      <ScrollContainer
        key="step-welcome"
        v-show="currentStep === 0"
        class="max-h-full *:first:mt-0 *:last:mb-0"
      >
        <h2>Welcome to the <span class="text-primary">usdx-dl</span> Setup</h2>
        <p>
          This setup wizard will guide you through the initial configuration of
          <code>usdx-dl</code>. Please follow the steps to ensure everything is set up
          correctly.
        </p>
      </ScrollContainer>
      <!-- step: songs folder -->
      <ScrollContainer
        key="step-songs-folder"
        v-show="currentStep === 1"
        class="max-h-full *:first:mt-0 *:last:mb-0"
      >
        <h2>Songs Folder</h2>
        <p>Please select the folder where you want to save your downloaded files.</p>
        <p>Currently, songs are saved in:</p>
        <SongsFolder editable />
      </ScrollContainer>
      <!-- step: usdb cookie -->
      <ScrollContainer
        key="step-usdb-cookie"
        v-show="currentStep === 2"
        class="max-h-full *:first:mt-0 *:last:mb-0"
      >
        <h2>USDB Cookie</h2>
        <UsdbCookie v-model="usdbCookieModel" />
      </ScrollContainer>
      <!-- step: download tools -->
      <ScrollContainer
        key="step-download-tools"
        v-show="currentStep === 3"
        class="max-h-full *:first:mt-0 *:last:mb-0"
      >
        <h2>Download Tools</h2>
        <DownloadTools />
      </ScrollContainer>
      <!-- step: done -->
      <ScrollContainer
        key="step-done"
        v-show="currentStep === 4"
        class="max-h-full *:first:mt-0 *:last:mb-0"
      >
        <h2>Setup Complete</h2>
        <p>🎉 Congratulations!</p>
        <p>
          You have successfully completed the setup of <code>usdx-dl</code>. You can now
          start using the application to download your favorite songs.
        </p>
        <Tabs>
          <p>
            <strong>Note:</strong> All settings can be changed later in the
            <TabLink id="dummy" class="*:disabled:opacity-100!" disabled
              >Settings</TabLink
            >
            tab.
          </p>
        </Tabs>
      </ScrollContainer>
    </TransitionGroup>
  </main>

  <footer class="container">
    <nav class="flex items-center justify-end gap-2 p-4">
      <Button v-if="currentStep > 0" variant="outline" @click="prevStep()">
        <ArrowLeft />
      </Button>
      <Button
        v-if="currentStep < numSteps - 1"
        variant="default"
        class="w-24"
        :disabled="!canContinue"
        @click="nextStep()"
      >
        <ArrowRight /> Next
      </Button>
      <Button
        v-else
        variant="success"
        class="w-24"
        :disabled="!canContinue"
        @click="setupComplete()"
      >
        <Check /> Finish
      </Button>
    </nav>
  </footer>
</template>

<style scoped>
/**
 * <TransitionGroup> transitions
 * https://vuejs.org/guide/built-ins/transition-group
 */
.setup-enter-active,
.setup-leave-active {
  position: absolute;
  top: 0;
  transition: all 0.3s ease-in-out;
}

.setup-enter-from,
.setup-leave-to {
  opacity: 0;
}

/* enter from right, leave to left */
.setup-forward .setup-enter-from {
  transform: translateX(10%);
}
.setup-forward .setup-leave-to {
  transform: translateX(-10%);
}

/* enter from left, leave to right */
.setup-backward .setup-enter-from {
  transform: translateX(-10%);
}
.setup-backward .setup-leave-to {
  transform: translateX(10%);
}
</style>
