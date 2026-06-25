<script lang="ts" setup>
import Button from "@/components/ui/button/Button.vue"
import Input from "@/components/ui/input/Input.vue"
import Label from "@/components/ui/label/Label.vue"
import RadioGroup from "@/components/ui/radio-group/RadioGroup.vue"
import RadioGroupItem from "@/components/ui/radio-group/RadioGroupItem.vue"
import Switch from "@/components/ui/switch/Switch.vue"
import type { Settings } from "@/types/api"
import { AlertTriangle, Check, Info, KeyRound } from "@lucide/vue"
import { computed, ref } from "vue"

const props = defineProps<{
  pinValid?: boolean
}>()

const settings = defineModel<Settings | null>("settings")
const pinValue = defineModel<string>("pin")
const pin = ref<string>(pinValue.value ?? "")
const pinEditable = ref<boolean>(false)
const requiresPin = computed(() => {
  const pinSet = new Set(settings.value?.pin ?? "")
  return pinSet.size === 1 && [...pinSet][0] === "*"
})
const locked = computed(() => requiresPin.value && props.pinValid !== true)

function updatePin() {
  pinEditable.value = false
  pinValue.value = pin.value
}
</script>

<template>
  <div class="bg-card flex flex-col gap-4 rounded border p-4">
    <template v-if="settings && requiresPin">
      <h3 class="text-lg font-bold">PIN</h3>
      <div class="grid w-fit grid-cols-[1fr_auto] items-center gap-2">
        <p class="text-muted-foreground col-span-2 text-sm">
          Settings impacting the worker processing the queue are protected by a PIN.
        </p>
        <Button
          v-if="!pinEditable"
          variant="outline"
          class="col-span-2 basis-full"
          @click="pinEditable = true"
        >
          <KeyRound />
          {{ pin ? "Edit" : "Enter" }} PIN
        </Button>
        <template v-else>
          <Input
            v-model="pin"
            id="input:settings:pin"
            type="password"
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
          class="bg-warning/10 border-warning text-warning col-span-2 flex w-auto flex-col justify-center rounded border p-2 text-center text-sm"
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
    <h3 class="text-lg font-bold">Download Options</h3>
    <div v-if="settings" class="grid grid-cols-[auto_1fr] items-center gap-2">
      <Label for="input:settings:usdb-cookie">USDB Cookie</Label>
      <Input
        v-model="settings.usdbCookie"
        id="input:settings:usdb-cookie"
        :disabled="locked"
        placeholder="PHPSESSID=..."
      />
      <details class="text-muted-foreground col-span-2 -mt-2 text-sm" :open="false">
        <summary class="cursor-pointer">How to get the PHPSESSID cookie?</summary>
        <ol class="list-outside list-decimal pl-4">
          <li>
            Go to
            <a href="https://usdb.animux.de" target="_blank" rel="noopener noreferrer">
              https://usdb.animux.de </a
            >.
          </li>
          <li>Login to your account.</li>
          <li>Open the browser's developer tools (F12).</li>
          <li>
            Run the following command in the console:
            <pre class="bg-muted mt-1 rounded p-2 text-sm whitespace-pre-wrap">
(await cookieStore.get("PHPSESSID")).value</pre
            >
          </li>
          <li>Copy the value and paste it into the above field.</li>
        </ol>
      </details>
    </div>
    <div v-if="settings" class="grid grid-cols-[auto_1fr] items-center gap-2">
      <Switch
        v-model="settings.noVideo"
        :disabled="locked"
        id="switch:settings:no-video"
      />
      <Label for="switch:settings:no-video">
        no video
        <span class="text-muted-foreground text-sm">[faster, less data]</span>
      </Label>
      <Switch
        v-model="settings.noLyrics"
        :disabled="locked"
        id="switch:settings:no-lyrics"
      />
      <Label for="switch:settings:no-lyrics">
        no lyrics
        <span class="text-muted-foreground text-sm">[less accurate]</span>
      </Label>
    </div>
    <hr />
    <h3 class="text-lg font-bold">AI Models</h3>
    <div v-if="settings">
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
      <RadioGroup v-model="settings.stemModel" class="items-start">
        <RadioGroupItem
          id="radio:stem-model:demucs"
          value="demucs"
          :disabled="locked"
          class="mt-0.5"
        />
        <Label for="radio:stem-model:demucs" class="block">
          Demucs
          <span class="text-muted-foreground text-sm">(recommended)</span>
        </Label>
        <RadioGroupItem
          id="radio:stem-model:mel-roformer"
          value="mel-roformer"
          :disabled="locked"
          class="mt-0.5"
        />
        <Label for="radio:stem-model:mel-roformer" class="block">
          Mel-Band Roformer
          <span class="text-muted-foreground text-sm"> [better, slow on CPU] </span>
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
      <RadioGroup v-model="settings.whisperModel" class="items-start">
        <RadioGroupItem
          id="radio:whisper-model:turbo"
          value="turbo"
          :disabled="locked"
          class="mt-0.5"
        />
        <Label for="radio:whisper-model:turbo" class="block">
          turbo
          <span class="text-muted-foreground text-sm">
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
          <span class="text-muted-foreground text-sm">[slow, highest quality]</span>
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
          <span class="text-muted-foreground text-sm">[fast, low quality]</span>
        </Label>
      </RadioGroup>
    </div>
  </div>
</template>
