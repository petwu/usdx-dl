import { ansiToHtml } from "@/lib/ansi"
import { websocketUrl } from "@/lib/host"
import { addError } from "@/store/errors"
import { $logBuffer } from "@/store/logs"
import { $settings } from "@/store/settings"
import { $songs } from "@/store/songs"
import { $progress, $state } from "@/store/state"
import { $downloadProgress, $tools } from "@/store/tools"
import type { MsgType } from "@/types/api"
import { atom } from "nanostores"

export const $ws = atom<WebSocket | null | undefined>(undefined)

export function connectWebSocket() {
  let ws = $ws.get()
  if (ws && ws.readyState === WebSocket.OPEN) {
    return
  }
  $logBuffer.set([])
  ws = new WebSocket(websocketUrl())
  ws.onmessage = (event) => {
    handleWebSocketMessage(event.data)
  }
  ws.onclose = () => {
    ws = null
  }
  $ws.set(ws)
}

export function disconnectWebSocket() {
  const ws = $ws.get()
  if (ws) {
    ws.close()
    $ws.set(null)
  }
}

type WebSocketMessage = {
  type: MsgType
  data: any
}

async function handleWebSocketMessage(msg: string) {
  if (!msg) return
  try {
    const { type, data }: WebSocketMessage = JSON.parse(msg)
    switch (type) {
      // stdout/stderr captured from the backend process
      case "log":
        const logBuffer = $logBuffer.get()
        const logLine = ansiToHtml(data.text)
        if (logBuffer.length > 0 && data.override) {
          logBuffer[logBuffer.length - 1] = logLine
            .replace(/^\r+/, "")
            .replace(/\n+$/, "")
        } else {
          logBuffer.push(logLine)
        }
        while (logBuffer.length > 1000) {
          logBuffer.shift()
        }
        $logBuffer.set([...logBuffer])
        break

      // error messages from e.g. the worker thread
      case "error":
        addError(data)
        break

      // updates to server-side state outside the setInterval fetches
      case "update":
        switch (data.what) {
          case "state":
            $state.set(data.payload)
            break
          case "settings":
            $settings.set(data.payload)
            break
          case "songs":
            $songs.set(data.payload)
            break
          case "tools":
            $tools.set(data.payload)
            break
          default:
            addError(`Unhandled update type: ${data.what}`, data)
        }
        break

      // progress updates from the worker thread
      case "progress":
        data.progress *= 100 // convert to percentage
        switch (data.what) {
          case "worker":
            $progress.set(data.progress)
            break
          case "tool":
            $downloadProgress.setKey(data.tool, data.progress)
            break
          default:
            addError(`Unhandled progress type: ${data.what}`, data)
        }
        break

      default:
        addError(`Unknown WebSocket message type: ${type}`, data)
    }
  } catch {
    addError("Failed to parse WebSocket message", msg)
  }
}
