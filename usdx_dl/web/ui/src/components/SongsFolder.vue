<script setup lang="ts">
import Button from "@/components/ui/button/Button.vue"
import { Folder } from "@lucide/vue"

const props = defineProps<{
  songsFolder?: string | null
}>()

const emit = defineEmits<{
  (e: "open-folder"): void
}>()
</script>

<template>
  <h3>Songs Folder</h3>
  <Button
    size="default"
    variant="ghost"
    class="w-fit rounded-none rounded-bl-lg text-amber-500 hover:bg-amber-500/10 hover:text-amber-500"
    title="open songs folder in file explorer"
    @click="emit('open-folder')"
  >
    <Folder />
    {{ props.songsFolder }}
  </Button>
  <p class="text-sm">
    The songs folder is where downloaded songs are stored. If you are using
    <i>UltraStar Deluxe</i>, add this to your
    <a href="https://usdx.eu/docs/config-ini" target="_blank" rel="noopener noreferrer"
      ><code>config.ini</code></a
    >:
  </p>
  <pre>
[Directories]
SongDir1={{ props.songsFolder }}
SongDir2=...</pre
  >
</template>
