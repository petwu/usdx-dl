import { apiUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import type { SongMetadata } from "@/types/api"
import { atom, onMount } from "nanostores"

export const $songs = atom<SongMetadata[]>([])
export const $songsFolder = atom<string | null>(null)

onMount($songs, () => {
  fetchSongs()
  const handle = setInterval(fetchSongs, 5000)
  return () => clearInterval(handle)
})

onMount($songsFolder, () => {
  fetchSongsFolder()
})

async function fetchSongs() {
  const response = await fetch(apiUrl("/songs"))
  if (response.ok) {
    $songs.set(await response.json())
  } else {
    await addError("Failed to fetch songs", response)
  }
}

async function fetchSongsFolder() {
  const response = await fetch(apiUrl("/songs/directory"))
  if (response.ok) {
    $songsFolder.set(await response.json())
  } else {
    await addError("Failed to fetch songs folder", response)
  }
}

export async function openSongFolder(id?: string) {
  fetch(apiUrl("/songs/directory"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  })
}
