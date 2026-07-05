export type ServerConfig = {
  setupDone: boolean
  unlockedSettings: boolean
  pauseProcessing: boolean
  isWebview: boolean
}

export type USDBSession = {
  browser: string
  username: string
  cookie: string
}

export type SongMetadata = {
  id: string
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
  pending: number
}

export type Tool = {
  name: string
  reason: string
  path: string
  version: string | null
  downloadRequired: boolean
  downloadPath: string
  downloadInfo: {
    version: string
    url: string
    sha256: string
  }
  homepage: string
  repository: string
  provider: string | null
  license: string
  licenseUrl: string
}

export type MsgType = "log" | "error" | "update"
