import { createMockStream, type MockController } from './mockStream'
import type { ChaosAction, ChaosCommand, TelemetryFrame } from './types'

const WS_URL = import.meta.env.VITE_OHMIC_WS_URL ?? 'ws://localhost:8765'
const STREAM_MODE = import.meta.env.VITE_OHMIC_STREAM ?? 'mock'

export type StreamClient = {
  connect: (onFrame: (frame: TelemetryFrame) => void, onStatus: (message: string) => void) => () => void
  sendChaos: (action: ChaosAction) => boolean
  isMock: boolean
  url: string
}

export const createStreamClient = (): StreamClient => {
  if (STREAM_MODE !== 'real') {
    let mock: MockController | null = null
    return {
      isMock: true,
      url: 'mock://contract-shaped-stream',
      connect: (onFrame) => {
        mock = createMockStream()
        return mock.start(onFrame)
      },
      sendChaos: (action) => {
        mock?.command(action)
        return true
      },
    }
  }

  let socket: WebSocket | null = null
  let closedByClient = false
  let reconnectTimer: number | null = null
  let attempts = 0
  let pendingAction: ChaosAction | null = null
  let currentStatus: ((message: string) => void) | null = null

  const clearReconnect = () => {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const sendCommand = (action: ChaosAction) => {
    if (socket?.readyState !== WebSocket.OPEN) {
      return false
    }
    const command: ChaosCommand = { type: 'chaos', target: 'PV_01', action }
    socket.send(JSON.stringify(command))
    return true
  }

  const flushPending = () => {
    if (pendingAction === null) return
    const action = pendingAction
    pendingAction = null
    if (sendCommand(action)) {
      currentStatus?.(`Sent ${action} command to PV_01`)
    } else {
      pendingAction = action
    }
  }

  return {
    isMock: false,
    url: WS_URL,
    connect: (onFrame, onStatus) => {
      closedByClient = false
      currentStatus = onStatus

      const connectSocket = () => {
        clearReconnect()
        socket = new WebSocket(WS_URL)
        socket.addEventListener('open', () => {
          attempts = 0
          onStatus(`Connected to ${WS_URL}`)
          flushPending()
        })
        socket.addEventListener('message', (event) => {
          try {
            onFrame(JSON.parse(event.data as string) as TelemetryFrame)
          } catch {
            onStatus('Received a malformed WebSocket frame')
          }
        })
        socket.addEventListener('close', () => {
          if (closedByClient) return
          const delay = Math.min(5000, 500 * 2 ** attempts)
          attempts += 1
          onStatus(`Disconnected from ${WS_URL}; reconnecting in ${Math.round(delay / 1000)}s`)
          reconnectTimer = window.setTimeout(connectSocket, delay)
        })
        socket.addEventListener('error', () => onStatus(`WebSocket error at ${WS_URL}`))
      }

      connectSocket()

      return () => {
        closedByClient = true
        clearReconnect()
        socket?.close()
        socket = null
        currentStatus = null
      }
    },
    sendChaos: (action) => {
      if (sendCommand(action)) {
        currentStatus?.(`Sent ${action} command to PV_01`)
        return true
      }
      pendingAction = action
      currentStatus?.(`Queued ${action} command until the WebSocket reconnects`)
      return false
    },
  }
}
