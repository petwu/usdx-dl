<script lang="ts" setup>
import ScrollContainer from "@/components/ScrollContainer.vue"
import SongsFolder from "@/components/SongsFolder.vue"
import ThemeSwitcher from "@/components/ThemeSwitcher.vue"
import Button from "@/components/ui/button/Button.vue"
import Input from "@/components/ui/input/Input.vue"
import Label from "@/components/ui/label/Label.vue"
import RadioGroup from "@/components/ui/radio-group/RadioGroup.vue"
import RadioGroupItem from "@/components/ui/radio-group/RadioGroupItem.vue"
import Switch from "@/components/ui/switch/Switch.vue"
import UsdbCookie from "@/components/UsdbCookie.vue"
import { $pin, $serverCfg, $settings } from "@/store/settings"
import { AlertTriangle, Check, Info, KeyRound, LoaderCircle } from "@lucide/vue"
import { useStore, useVModel } from "@nanostores/vue"
import { computed, ref } from "vue"

const settings = useStore($settings)
const serverCfg = useStore($serverCfg)
const pin = useStore($pin)
const haveSettings = computed(
  () => settings.value !== null && JSON.stringify(settings.value) !== "{}",
)

const {
  usdbCookieModel,
  stemModelModel,
  whisperModelModel,
  noLyricsModel,
  noVideoModel,
} = useVModel($settings, [
  "usdbCookie",
  "stemModel",
  "whisperModel",
  "noLyrics",
  "noVideo",
])

const pinModel = ref<string>(pin.value.value ?? "")
const pinEditable = ref<boolean>(false)
const requiresPin = computed(() => {
  const pinSet = new Set(settings.value?.pin ?? "")
  return pinSet.size === 1 && [...pinSet][0] === "*"
})
const locked = computed(() => requiresPin.value && pin.value.valid !== true)

function updatePin() {
  pinEditable.value = false
  $pin.setKey("value", pinModel.value)
}
</script>

<template>
  <div class="bg-card h-full rounded border">
    <ScrollContainer direction="y" class="h-full">
      <div class="prose w-full max-w-full p-4 [&_hr]:my-8">
        <template v-if="haveSettings && requiresPin">
          <h3>PIN</h3>
          <p class="col-span-2 text-sm">
            Settings impacting the worker processing the queue are protected by a PIN.
          </p>
          <div class="grid w-full grid-cols-[1fr_auto] items-center gap-2 sm:w-100">
            <Button
              v-if="!pinEditable"
              variant="outline"
              class="col-span-2 basis-full"
              @click="pinEditable = true"
            >
              <KeyRound />
              {{ pinModel ? "Edit" : "Enter" }} PIN
            </Button>
            <template v-else>
              <Input
                v-model="pinModel"
                id="input:settings:pin"
                type="password"
                inputmode="numeric"
                autocomplete="off"
                placeholder="****"
                :disabled="!pinEditable"
                @keyup.enter="updatePin"
              />
              <Button
                size="icon"
                variant="success"
                title="confirm PIN entry"
                @click="updatePin"
              >
                <Check />
              </Button>
            </template>
            <div
              v-if="locked"
              class="not-prose bg-warning/10 border-warning text-warning col-span-2 flex w-auto flex-col justify-center rounded border p-2 text-center text-sm"
            >
              <p class="flex items-center justify-center gap-2 font-bold">
                <AlertTriangle :size="16" /> Worker settings are locked.
              </p>
              <p>Please enter the correct PIN to unlock them.</p>
            </div>
            <div
              v-else
              class="bg-success/10 border-success text-success col-span-2 flex w-auto flex-col justify-center rounded border p-2 text-center text-sm"
            >
              <p class="flex items-center justify-center gap-2 font-bold">
                <Check :size="16" /> Worker settings are unlocked.
              </p>
            </div>
          </div>
          <hr />
        </template>
        <template v-if="haveSettings">
          <h3>Download Options</h3>
          <UsdbCookie v-model="usdbCookieModel" :disabled="locked" collapsed />
          <div class="mt-4 grid grid-cols-[auto_1fr] items-center gap-2">
            <Switch
              v-model="noVideoModel"
              :disabled="locked"
              id="switch:settings:no-video"
            />
            <Label for="switch:settings:no-video">
              no video
              <span class="text-muted-foreground text-sm font-light"
                >[faster, less data]</span
              >
            </Label>
            <Switch
              v-model="noLyricsModel"
              :disabled="locked"
              id="switch:settings:no-lyrics"
            />
            <Label for="switch:settings:no-lyrics">
              no lyrics
              <span class="text-muted-foreground text-sm font-light"
                >[less accurate]</span
              >
            </Label>
          </div>
          <hr />
          <h3>AI Models</h3>
          <div>
            <h4 class="flex items-center gap-3">
              Stem Separation Model
              <a
                href="https://github.com/nomadkaraoke/python-audio-separator"
                target="_blank"
                rel="noopener noreferrer"
                class="text-blue-500 hover:underline"
              >
                <Info :size="16" />
              </a>
            </h4>
            <RadioGroup v-model="stemModelModel" class="items-start">
              <RadioGroupItem
                id="radio:stem-model:demucs"
                value="demucs"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:stem-model:demucs" class="block">
                Demucs
                <span class="text-muted-foreground text-sm font-light"
                  >(recommended)</span
                >
              </Label>
              <RadioGroupItem
                id="radio:stem-model:mel-roformer"
                value="mel-roformer"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:stem-model:mel-roformer" class="block">
                Mel-Band Roformer
                <span class="text-muted-foreground text-sm font-light">
                  [better, slow on CPU]
                </span>
              </Label>
            </RadioGroup>
            <h4 class="flex items-center gap-3">
              Transcription Model (WhisperX)
              <a
                href="https://github.com/openai/whisper/discussions/2363"
                target="_blank"
                rel="noopener noreferrer"
                class="text-blue-500 hover:underline"
              >
                <Info :size="16" />
              </a>
            </h4>
            <RadioGroup v-model="whisperModelModel" class="items-start">
              <RadioGroupItem
                id="radio:whisper-model:turbo"
                value="turbo"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:whisper-model:turbo" class="block">
                turbo
                <span class="text-muted-foreground text-sm font-light">
                  (recommended) [fast, high quality]
                </span>
              </Label>
              <RadioGroupItem
                id="radio:whisper-model:large"
                value="large"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:whisper-model:large" class="block">
                large
                <span class="text-muted-foreground text-sm font-light"
                  >[slow, highest quality]</span
                >
              </Label>
              <RadioGroupItem
                id="radio:whisper-model:medium"
                value="medium"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:whisper-model:medium" class="block">medium</Label>
              <RadioGroupItem
                id="radio:whisper-model:small"
                value="small"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:whisper-model:small" class="block">small</Label>
              <RadioGroupItem
                id="radio:whisper-model:base"
                value="base"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:whisper-model:base" class="block">base</Label>
              <RadioGroupItem
                id="radio:whisper-model:tiny"
                value="tiny"
                :disabled="locked"
                class="mt-0.5"
              />
              <Label for="radio:whisper-model:tiny" class="block">
                tiny
                <span class="text-muted-foreground text-sm font-light"
                  >[fast, low quality]</span
                >
              </Label>
            </RadioGroup>
          </div>
        </template>
        <div v-else>
          <p class="text-muted-foreground text-sm">
            <LoaderCircle class="-mt-1 inline-block size-4 animate-spin" />
            Loading settings ...
          </p>
        </div>
        <hr />
        <h3>Songs Folder</h3>
        <SongsFolder editable />
        <template v-if="serverCfg.isWebview">
          <hr />
          <h3>Theme</h3>
          <ThemeSwitcher fancy />
        </template>
      </div>
    </ScrollContainer>
  </div>
</template>
