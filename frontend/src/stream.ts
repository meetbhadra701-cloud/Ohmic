import { createMockStream, type MockController } from './mockStream'
import type { ChaosAction, ChaosCommand, TelemetryFrame } from './types'

const WS_URL = import.meta.env.VITE_OHMIC_WS_URL ?? 'ws://localhost:8765'
const STREAM_MODE = import.meta.env.VITE_OHMIC_STREAM ?? 'mock'

export type StreamClient = {
  connect: (onFrame: (frame: TelemetryFrame) => void, onStatus: (message: string) => void) => () => void
  sendChaos: (action: ChaosAction) => void
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
      sendChaos: (action) => mock?.command(action),
    }
  }

  let socket: WebSocket | null = null

  return {
    isMock: false,
    url: WS_URL,
    connect: (onFrame, onStatus) => {
      socket = new WebSocket(WS_URL)
      socket.addEventListener('open', () => onStatus(`Connected to ${WS_URL}`))
      socket.addEventListener('message', (event) => {
        try {
          onFrame(JSON.parse(event.data as string) as TelemetryFrame)
        } catch {
          onStatus('Received a malformed WebSocket frame')
        }
      })
      socket.addEventListener('close', () => onStatus(`Disconnected from ${WS_URL}`))
      socket.addEventListener('error', () => onStatus(`WebSocket error at ${WS_URL}`))

      return () => {
        socket?.close()
        socket = null
      }
    },
    sendChaos: (action) => {
      if (socket?.readyState !== WebSocket.OPEN) {
        return
      }
      const command: ChaosCommand = { type: 'chaos', target: 'PV_01', action }
      socket.send(JSON.stringify(command))
    },
  }
}
