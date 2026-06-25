function getHost(): URL {
  const host = new URL(window.location.href)
  if (import.meta.env.DEV) {
    // during production, frontend and backend are served by the same server,
    // but during development, the frontend may be served by a different server
    // (e.g. vite dev server), so we need to adjust the port
    host.port = "8000"
  }
  return host
}

export function apiUrl(route: string): string {
  const host = getHost()
  return new URL(`api/${route}`, host).toString()
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
