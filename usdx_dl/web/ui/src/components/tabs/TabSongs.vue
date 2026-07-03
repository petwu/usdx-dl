<script setup lang="ts">
import ScrollContainer from "@/components/ScrollContainer.vue"
import { SongCard } from "@/components/parts"
import Input from "@/components/ui/input/Input.vue"
import { $songs } from "@/store/songs"
import { useStore } from "@nanostores/vue"
import { computed, ref } from "vue"

const songs = useStore($songs)
const songsFilter = ref<string>("")
const filteredSongs = computed(() => {
  if (!songsFilter.value) {
    return songs.value
  }
  const filter = songsFilter.value.toLowerCase()
  return songs.value.filter(
    (song) =>
      song.artist.toLowerCase().includes(filter) ||
      song.title.toLowerCase().includes(filter),
  )
})
</script>

<template>
  <div class="flex h-full flex-col gap-2">
    <div class="grow-0">
      <div class="flex items-center">
        <Input v-model="songsFilter" placeholder="Filter songs ..." />
        <span
          class="text-muted-foreground shrink-0 text-right text-sm tabular-nums"
          :style="{ minWidth: songs.length.toString().length * 2 + 2 + 'ch' }"
        >
          {{ filteredSongs.length }}/{{ songs.length }}
        </span>
      </div>
    </div>
    <ScrollContainer direction="y" class="grow">
      <TransitionGroup
        tag="ul"
        name="songs"
        class="xs:grid-cols-[repeat(auto-fit,minmax(320px,1fr))] grid grid-cols-1 gap-2"
      >
        <SongCard
          as="li"
          v-for="song in filteredSongs"
          :key="JSON.stringify(song)"
          :song="song"
        />
      </TransitionGroup>
    </ScrollContainer>
  </div>
</template>

<style scoped>
/**
 * <TransitionGroup> transitions
 * https://vuejs.org/guide/built-ins/transition-group
 */
.songs-move,
.songs-enter-active,
.songs-leave-active {
  position: relative;
  transition: all 0.25s ease;
}
.songs-enter-from,
.songs-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
