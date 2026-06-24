<script setup lang="ts">
import MusicBars from "@/components/MusicBars.vue"
import { useCurrentSong } from "@/components/store"
import { Button } from "@/components/ui/button"
import { getAssetUrl } from "@/lib/host"
import { cn } from "@/lib/utils"
import type { SongMetadata } from "@/types/api"
import { Pause, Play } from "@lucide/vue"
import { ref, useTemplateRef, watch, type HTMLAttributes } from "vue"

const props = withDefaults(
  defineProps<{
    as?: string
    song: SongMetadata & { id: string }
    disabled?: boolean
    class?: HTMLAttributes["class"]
  }>(),
  {
    as: "div",
    disabled: false,
  },
)

const audio = useTemplateRef("audioRef")
const { currentSong } = useCurrentSong()

const meta = props.song
const playing = ref(false)
const progress = ref(0.0)

watch(playing, (newVal) => {
  if (!audio.value) return
  if (newVal) {
    currentSong.value = meta.id
    audio.value.play()
  } else {
    audio.value.pause()
  }
})
watch(
  () => audio.value,
  () => {
    audio.value?.addEventListener("timeupdate", () => {
      if (!audio.value) return
      progress.value = audio.value.currentTime / audio.value.duration
    })
  },
)
watch(
  () => currentSong.value,
  (newVal) => {
    if (newVal !== meta.id) {
      playing.value = false
    }
  },
)

function seek(event: MouseEvent) {
  if (!audio.value) return
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const newProgress = clickX / rect.width
  audio.value.currentTime = newProgress * audio.value.duration
}
</script>

<template>
  <component
    :is="props.as"
    :class="
      cn(
        'bg-card overflow-hidden rounded border p-0',
        'relative grid grid-cols-[auto_1fr] gap-2',
        props.class,
      )
    "
  >
    <img
      :src="getAssetUrl(meta.id, 'cover')"
      alt="cover"
      class="h-full min-h-24 w-24 shrink-0 object-cover"
    />
    <div class="grow">
      <Button
        size="icon"
        variant="ghost"
        :disabled="props.disabled"
        class="text-primary float-right rounded-none rounded-bl-lg"
        @click="playing = !playing"
      >
        <Play v-if="!playing" />
        <Pause v-else />
      </Button>
      <audio
        ref="audioRef"
        :src="getAssetUrl(meta.id, 'audio')"
        :controls="false"
        preload="metadata"
        class="hidden"
      />
      <h3 class="flex items-center gap-2 font-bold">
        <MusicBars v-if="playing" class="size-4" />
        {{ meta.title }}
      </h3>
      <p class="text-sm">{{ meta.artist }}</p>
      <p class="text-muted-foreground mt-0.5 text-xs italic">
        {{ [meta.year, meta.genre, meta.language].filter(Boolean).join(", ") }}
      </p>
    </div>
    <div
      class="absolute right-0 bottom-0 left-24 flex h-4 cursor-pointer items-end"
      @click="seek"
    >
      <div class="bg-primary h-1" :style="{ width: `${progress * 100}%` }" />
    </div>
  </component>
</template>
