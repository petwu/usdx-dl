import { ref } from "vue"

const currentSong = ref<string | null>(null)

export function useCurrentSong() {
  return { currentSong }
}
