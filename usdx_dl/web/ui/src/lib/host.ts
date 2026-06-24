function getHost(): URL {
  return new URL(window.location.href)
}

export function apiUrl(): string {
  const host = getHost()
  return new URL("api", host).toString()
}

export function websocketUrl(): string {
  const host = getHost()
  return `ws://${host.hostname}:${host.port}/ws`
}

export type AssetType = "cover" | "audio"
export function getAssetUrl(songId: string, assetType: AssetType): string {
  const filename = {
    cover: "cover.jpg",
    audio: "audio.mp3",
  }[assetType]
  if (!filename) {
    throw new Error(`Invalid assetType value: ${assetType}`)
  }
  const host = getHost()
  return new URL(`songs/${songId}/${filename}`, host).toString()
}
