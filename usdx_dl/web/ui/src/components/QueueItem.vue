<script setup lang="ts">
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { PipelineContext } from "@/types/api"
import {
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowDownToLine,
  ArrowUp,
  ArrowUpToLine,
  Check,
  LoaderCircle,
  Pencil,
  PencilOff,
  Play,
  RefreshCw,
  Save,
  Trash2,
  UndoDot,
} from "@lucide/vue"
import { computed, ref, toRaw, watch, type HTMLAttributes } from "vue"

const props = withDefaults(
  defineProps<{
    as?: string
    item: PipelineContext
    index?: number
    size?: number
    isProcessing?: boolean
    disabled?: boolean
    class?: HTMLAttributes["class"]
  }>(),
  {
    as: "div",
    isProcessing: false,
    disabled: false,
  },
)

const meta = ref(structuredClone(toRaw(props.item.meta)))
const lyrics = ref(structuredClone(toRaw(props.item.lyrics)))
const editable = ref<boolean>(false)
const updating = ref<boolean>(false)
const modified = computed(
  () => !deepEqual(meta.value, props.item.meta) || lyrics.value !== props.item.lyrics,
)

watch(
  () => props.item.meta,
  (newMeta) => {
    if (!editable.value) {
      meta.value = structuredClone(toRaw(newMeta))
    }
  },
)

// cSpell: disable-next-line
const youtubeRegex = /(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|v\/))([^&\n?#]+)/

const emit = defineEmits<{
  (e: "move", item: PipelineContext, direction: "up" | "down", toEnd: boolean): void
  (e: "update", item: PipelineContext, done: () => void): void
  (e: "remove", item: PipelineContext): void
  (e: "retry", item: PipelineContext): void
}>()

function deepEqual<T>(a: T, b: T): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

function resetChanges() {
  meta.value = structuredClone(toRaw(props.item.meta))
  lyrics.value = structuredClone(toRaw(props.item.lyrics))
  editable.value = false
}

function persistChanges(reviewed: boolean | undefined) {
  const updatedItem: PipelineContext = {
    ...props.item,
    lyrics: lyrics.value,
    meta: structuredClone(toRaw(meta.value)),
  }
  if (reviewed !== undefined) {
    updatedItem.reviewed = reviewed
  }
  updating.value = true
  emit("update", updatedItem, () => {
    updating.value = false
  })
  editable.value = false
}

const lyricsSearchUrl = computed(
  () =>
    "https://www.google.com/search?q=" +
    encodeURIComponent(`${meta.value.title} ${meta.value.artist} lyrics "lrc"`),
)
</script>

<template>
  <component
    :is="props.as"
    :class="
      cn(
        'bg-card overflow-hidden rounded border p-0',
        'grid grid-cols-[auto_1fr] grid-rows-[auto_auto] gap-2',
        'md:grid-cols-[auto_1fr_auto] md:grid-rows-[auto]',
        isProcessing && 'border-primary! bg-primary/10 grid-rows-[auto]',
        props.item.reviewed === false && 'border-fuchsia-500! bg-fuchsia-500/10',
        props.class,
      )
    "
  >
    <img
      v-if="meta.coverUrl"
      :src="meta.coverUrl"
      alt="cover"
      class="size-24 shrink-0 rounded-br-lg object-cover"
    />
    <div v-else class="bg-muted size-24 shrink-0 rounded-br-lg" />
    <div :class="cn('grow', editable && 'max-md:pr-0.5')">
      <h3 v-if="!editable" class="font-bold">{{ meta.title }}</h3>
      <Input
        v-else
        v-model="meta.title"
        :disabled="props.disabled"
        placeholder="Title"
        class="my-0.5 h-7 p-1 text-base font-bold ring-0!"
      />
      <p v-if="!editable" class="text-sm">{{ meta.artist }}</p>
      <Input
        v-else
        placeholder="Artist"
        v-model="meta.artist"
        :disabled="props.disabled"
        class="my-0.5 h-6 p-1 text-sm ring-0!"
      />
      <p class="text-muted-foreground text-sm italic">
        <span v-if="!editable">{{
          [meta.year, meta.genre, meta.language].filter(Boolean).join(", ")
        }}</span>
        <span v-else class="flex gap-1">
          <Input
            v-model="meta.year"
            type="text"
            inputmode="numeric"
            pattern="[0-9]*"
            autocomplete="off"
            :disabled="props.disabled"
            placeholder="Year"
            class="my-0.5 h-6 p-1 text-sm italic ring-0!"
          />
          <Input
            v-model="meta.genre"
            :disabled="props.disabled"
            placeholder="Genre"
            class="my-0.5 h-6 p-1 text-sm italic ring-0!"
          />
          <Input
            v-model="meta.language"
            :disabled="props.disabled"
            placeholder="Language"
            class="my-0.5 h-6 p-1 text-sm italic ring-0!"
          />
        </span>
      </p>
      <p>
        <a
          v-if="meta.videoUrl && !editable"
          :href="meta.videoUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-sm"
        >
          <Play :size="16" />
          <template v-if="meta.videoUrl.match(youtubeRegex)">
            YouTube ({{ meta.videoUrl.match(youtubeRegex)![1] }})
          </template>
          <template v-else>Video</template>
        </a>
        <Input
          v-else-if="editable"
          v-model="meta.videoUrl"
          :disabled="props.disabled"
          placeholder="Video URL"
          class="my-0.5 h-6 p-1 text-sm ring-0!"
        />
      </p>
      <Badge
        v-if="!meta.usdbUrl"
        variant="warning"
        class="mt-1 inline-block whitespace-normal"
      >
        <AlertTriangle class="-mt-0.5 mr-0.5 inline" /> Requires transcription.
        <strong>{{ lyrics ? "With lyrics." : "No lyrics." }}</strong>
      </Badge>
      <Badge
        v-if="isProcessing"
        variant="default"
        class="my-1 cursor-pointer"
        @click="$emit('click-badge')"
      >
        <LoaderCircle class="animate-spin" /> Processing ...
      </Badge>
    </div>
    <template v-if="!props.isProcessing && !meta.usdbUrl">
      <div
        v-if="!editable"
        class="max-h-24 overflow-y-auto p-2 text-xs wrap-break-word whitespace-pre-wrap max-md:col-span-2 md:col-span-3"
      >
        <p v-if="lyrics" v-for="line in lyrics.split('\n')" :key="line">{{ line }}</p>
        <p v-else class="text-muted-foreground whitespace-normal italic">
          No lyrics found. Please
          <a :href="lyricsSearchUrl" target="_blank" rel="noopener noreferrer">
            search for them on Google
          </a>
          then edit
          <span class="whitespace-pre">[<Pencil class="inline size-3" />]</span>
          the item and paste the synched lyrics (<a
            href="https://en.wikipedia.org/wiki/LRC_(file_format)"
            target="_blank"
            rel="noopener noreferrer"
            >LRC format</a
          >).
        </p>
      </div>
      <Textarea
        v-else
        v-model="lyrics"
        :disabled="props.disabled"
        placeholder="[00:00.15] Is this the real life? Is this just fantasy?
[00:07.13] Caught in a landslide, no escape from reality
..."
        class="m-1 max-h-24 w-[calc(100%-0.5rem)] text-xs! max-md:col-span-2 md:col-span-3"
      />
    </template>
    <p
      v-if="props.item.reviewed === false"
      class="col-span-2 px-2 text-sm text-fuchsia-500 md:col-span-3 md:pb-2"
    >
      Please review the metadata
      <span v-if="props.item.lyrics">and lyrics</span> for accuracy and make any
      necessary edits before continuing with the processing.
    </p>
    <div v-else-if="props.item.errors" class="col-span-2 p-2 md:col-span-3">
      <div class="text-destructive flex items-center gap-2">
        <AlertCircle :size="16" />
        <span>Processing failed.</span>
      </div>
      <details class="text-destructive text-sm">
        <summary>Details</summary>
        <ul class="list-disc pl-4">
          <li v-for="(error, index) in props.item.errors" :key="index">
            {{ error }}
          </li>
        </ul>
      </details>
    </div>
    <div
      v-if="!props.isProcessing"
      class="flex flex-row justify-end max-md:col-span-2 md:col-start-3 md:row-start-1 md:mt-2 md:mr-2"
    >
      <ButtonGroup
        :class="
          cn(
            '*:disabled:*:opacity-25 *:disabled:opacity-100',
            'max-md:*:border-b-0 max-md:*:first:rounded-tl-none max-md:*:first:border-l-0 max-md:*:last:rounded-br-none',
          )
        "
      >
        <Button
          size="icon"
          variant="outline"
          title="move up"
          :disabled="props.index === 0 || props.disabled"
          @click="emit('move', props.item, 'up', false)"
        >
          <ArrowUp />
        </Button>
        <Button
          size="icon"
          variant="outline"
          title="move down"
          :disabled="props.index === (props.size ?? 1) - 1 || props.disabled"
          @click="emit('move', props.item, 'down', false)"
        >
          <ArrowDown />
        </Button>
        <Button
          size="icon"
          variant="outline"
          title="process next"
          :disabled="props.index === 0 || props.disabled"
          @click="emit('move', props.item, 'up', true)"
        >
          <ArrowUpToLine />
        </Button>
        <Button
          size="icon"
          variant="outline"
          title="process last"
          :disabled="props.index === (props.size ?? 1) - 1 || props.disabled"
          @click="emit('move', props.item, 'down', true)"
        >
          <ArrowDownToLine />
        </Button>
      </ButtonGroup>
      <div class="grow md:w-4 md:grow-0"></div>
      <ButtonGroup
        :class="
          cn(
            '*:disabled:*:opacity-25 *:disabled:opacity-100',
            'max-md:*:border-b-0 max-md:*:first:rounded-bl-none max-md:*:last:rounded-tr-none max-md:*:last:border-r-0',
          )
        "
      >
        <template v-if="!editable">
          <Button
            size="icon"
            variant="outline"
            title="edit"
            @click="editable = true"
            :disabled="props.disabled"
          >
            <Pencil v-if="!updating" />
            <LoaderCircle v-else class="animate-spin" />
          </Button>
          <Button
            v-if="props.item.reviewed === false"
            size="icon"
            title="mark as reviewed"
            :disabled="props.disabled"
            @click="persistChanges(true)"
            class="bg-fuchsia-500 text-white hover:bg-fuchsia-600"
          >
            <Check />
          </Button>
          <Button
            v-else-if="props.item.errors"
            size="icon"
            variant="warning"
            title="retry"
            :disabled="props.disabled"
            @click="emit('retry', props.item)"
          >
            <RefreshCw />
          </Button>
          <Button
            v-else
            size="icon"
            variant="destructive"
            title="remove from queue"
            :disabled="props.disabled"
            @click="emit('remove', props.item)"
          >
            <Trash2 />
          </Button>
        </template>
        <template v-else>
          <Button
            v-if="!modified"
            size="icon"
            variant="outline"
            title="save changes"
            @click="editable = false"
            :disabled="props.disabled"
          >
            <PencilOff />
          </Button>
          <Button
            v-else
            size="icon"
            variant="destructive"
            title="discard changes"
            :disabled="props.disabled"
            @click="resetChanges"
          >
            <UndoDot />
          </Button>
          <Button
            size="icon"
            variant="success"
            title="save changes"
            :disabled="!modified || props.disabled"
            @click="persistChanges(undefined)"
          >
            <Save />
          </Button>
        </template>
      </ButtonGroup>
    </div>
  </component>
</template>
