export type SongMetadata = {
  title: string
  artist: string
  year: number
  genre: string | null
  language: string | null
  usdbUrl: string | null
  videoUrl: string | null
  coverUrl: string | null
  bgUrl: string | null
}

export type Settings = {
  pin: string | null
  usdbCookie: string | null
  stemModel: string
  whisperModel: string
  noLyrics: boolean
  noVideo: boolean
  pauseProcessing: boolean
}

export type PipelineContext = Omit<Settings, "pauseProcessing" | "pin"> & {
  uuid: string
  lyrics: string | null
  meta: SongMetadata
  reviewed: boolean | null
  errors: string[] | null
}

export type ServerState = {
  processing: PipelineContext | null
  queue: PipelineContext[]
}

export type Tool = {
  name: string
  path: string
  version: string | null
  latest: string
  downloadUrl: string
  homepage: string
}
