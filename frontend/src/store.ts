import { create } from 'zustand'
import type { DemandPoint, StreamStatus, TelemetryFrame } from './types'

type TelemetryState = {
  frame: TelemetryFrame | null
  history: DemandPoint[]
  status: StreamStatus
  lowPower: boolean
  lastMessage: string
  setFrame: (frame: TelemetryFrame) => void
  setStatus: (status: StreamStatus, message?: string) => void
  setLowPower: (lowPower: boolean) => void
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  frame: null,
  history: [],
  status: 'mock',
  lowPower: true,
  lastMessage: 'Mock stream ready',
  setFrame: (frame) =>
    set((state) => ({
      frame,
      history: [
        ...state.history.slice(-47),
        {
          tick: frame.tick,
          sim_time: frame.sim_time,
          actual: frame.forecast.actual_demand_kw,
          predicted: frame.forecast.predicted_demand_kw,
        },
      ],
      lastMessage:
        frame.alerts[0]?.detail ??
        `${frame.mode === 'CRITICAL' ? 'Critical mode' : 'Normal mode'} at ${frame.sim_time}`,
    })),
  setStatus: (status, message) =>
    set({
      status,
      lastMessage: message ?? status,
    }),
  setLowPower: (lowPower) => set({ lowPower }),
}))
