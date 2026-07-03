<script setup lang="ts">
import Button from "@/components/ui/button/Button.vue"
import { $setup } from "@/store/settings"
import {
  $songsFolder,
  checkFolder,
  chooseSongFolder,
  openSongFolder,
} from "@/store/songs"
import { Check, Folder, FolderInput, FolderSearch, X } from "@lucide/vue"
import { useStore } from "@nanostores/vue"
import { ref } from "vue"

const props = defineProps<{
  editable?: boolean
}>()

const songsFolder = useStore($songsFolder)
const valid = ref<boolean>(false)

$songsFolder.subscribe(async (folder) => {
  valid.value = folder ? await checkFolder(folder) : false
  $setup.setKey("songsFolder", valid.value)
})
</script>

<template>
  <template v-if="songsFolder">
    <div class="flex items-center gap-2">
      <Button
        size="default"
        variant="ghost"
        class="w-fit bg-amber-500/10 text-amber-500 hover:bg-amber-500/15 hover:text-amber-500"
        title="open songs folder in file explorer"
        @click="openSongFolder()"
      >
        <Folder />
        {{ songsFolder }}
      </Button>
      <Check v-if="valid" class="text-success size-6" title="valid folder" />
      <X
        v-else-if="songsFolder"
        class="text-destructive size-6"
        title="invalid folder"
      />
    </div>
    <div v-if="props.editable" class="mt-2 flex gap-2">
      <Button
        variant="outline"
        title="select a different folder, leave the current one as is"
        @click="chooseSongFolder(false)"
      >
        <FolderSearch /> Select Different Folder
      </Button>
      <Button
        variant="outline"
        title="move the songs folder to a new location"
        @click="chooseSongFolder(true)"
      >
        <FolderInput /> Move Folder
      </Button>
    </div>
    <p class="text-sm">
      The songs folder is where downloaded songs are stored. If you are using
      <i>UltraStar Deluxe</i>, add this to your
      <a
        href="https://usdx.eu/docs/config-ini"
        target="_blank"
        rel="noopener noreferrer"
        ><code>config.ini</code></a
      >:
    </p>
    <pre>
[Directories]
SongDir1={{ songsFolder }}
SongDir2=...</pre>
  </template>
</template>
