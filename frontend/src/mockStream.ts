import type { ChaosAction, TelemetryFrame } from './types'

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value))

const formatSimTime = (tick: number) => {
  const minutes = (tick * 15) % (24 * 60)
  const hh = Math.floor(minutes / 60)
  const mm = minutes % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

export type MockController = {
  start: (onFrame: (frame: TelemetryFrame) => void) => () => void
  command: (action: ChaosAction) => void
}

export const createMockStream = (): MockController => {
  let killed = false
  let lastActionTick = 0
  let tick = 96

  const command = (action: ChaosAction) => {
    killed = action === 'kill'
    lastActionTick = tick
  }

  const buildFrame = (): TelemetryFrame => {
    tick += 1
    const phase = (tick % 96) / 96
    const sunCurve = Math.max(0, Math.sin(Math.PI * phase))
    const loadWave = Math.sin(phase * Math.PI * 2 - 0.8)
    const demand = 94 + loadWave * 18 + Math.sin(tick / 3) * 4
    const critical = demand * 0.4
    const solarOutput = killed ? 0 : sunCurve * 78
    const inRecoveryWindow = killed && tick - lastActionTick < 48
    const served = killed ? critical + Math.max(0, solarOutput * 0.15) : demand
    const shed = Math.max(0, demand - served)
    const batteryFlow = killed ? Math.min(50, critical) : solarOutput > demand ? -18 : 28
    const batterySoc = clamp(0.82 - Math.max(0, tick - 100) * 0.0009 - (killed ? 0.08 : 0), 0.2, 0.94)
    const mode = killed ? 'CRITICAL' : 'NORMAL'
    const batteryMode = killed ? 'grid_forming' : 'market'

    return {
      schema_version: 1,
      tick,
      sim_time: formatSimTime(tick),
      day_phase: Number(phase.toFixed(3)),
      mode,
      nodes: {
        PV_01: {
          type: 'solar',
          output_kw: Number(solarOutput.toFixed(1)),
          alive: !killed,
          health: killed ? 'fault' : 'nominal',
        },
        BESS_01: {
          type: 'battery',
          soc: Number(batterySoc.toFixed(3)),
          soc_percent: Number((batterySoc * 100).toFixed(1)),
          flow_kw: Number(batteryFlow.toFixed(1)),
          max_discharge_kw: 50,
          mode: batteryMode,
          ask_price_usd_kwh: killed ? null : 0.18,
          unmet_kw: killed && critical > 50 ? Number((critical - 50).toFixed(1)) : 0,
          health: batterySoc < 0.28 ? 'degraded' : 'nominal',
        },
        LOAD_CAMPUS: {
          type: 'load',
          demand_kw: Number(demand.toFixed(1)),
          critical_kw: Number(critical.toFixed(1)),
          served_kw: Number(served.toFixed(1)),
          shed_kw: Number(shed.toFixed(1)),
          health: shed > 0 ? 'degraded' : 'nominal',
        },
      },
      market: {
        clearing_price_usd_kwh: killed ? null : Number((0.21 + sunCurve * 0.06).toFixed(3)),
        flows: killed
          ? [{ from: 'BESS_01', to: 'LOAD_CAMPUS', kw: Number(Math.min(50, critical).toFixed(1)), curtailed_kw: 0 }]
          : [
              { from: solarOutput > 10 ? 'PV_01' : 'BESS_01', to: 'LOAD_CAMPUS', kw: Number(Math.min(demand, Math.max(18, solarOutput || 32)).toFixed(1)), curtailed_kw: 0 },
            ],
        unmet_kw: killed && critical > 50 ? Number((critical - 50).toFixed(1)) : 0,
        surplus_kw: killed ? 0 : Number(Math.max(0, solarOutput - demand).toFixed(1)),
        curtailed_kw: killed ? 0 : Number(Math.max(0, solarOutput - 80).toFixed(1)),
        per_line_flow_kw: { FEEDER_1: Number(Math.min(80, Math.abs(batteryFlow) + solarOutput * 0.45).toFixed(1)) },
      },
      forecast: {
        predicted_demand_kw: Number((demand + 12 + Math.sin(tick / 7) * 3).toFixed(1)),
        horizon_ticks: 5,
        actual_demand_kw: Number(demand.toFixed(1)),
        cond: Number((980 + Math.abs(Math.sin(tick / 9)) * 420).toFixed(1)),
        reanchor_count: Math.floor(tick / 120),
        warm: tick > 20,
      },
      alerts: killed
        ? [
            {
              level: 'CRITICAL',
              type: 'SOLAR_LOSS',
              detail: inRecoveryWindow ? 'PV_01 missed 3 heartbeats; battery grid-forming' : 'PV_01 remains isolated',
              tick: lastActionTick,
            },
          ]
        : lastActionTick > 0
          ? [{ level: 'ALL_CLEAR', type: 'SOLAR_LOSS', detail: 'PV_01 heartbeat restored', tick: lastActionTick }]
          : [],
    }
  }

  const start = (onFrame: (frame: TelemetryFrame) => void) => {
    onFrame(buildFrame())
    const id = window.setInterval(() => onFrame(buildFrame()), 1000)
    return () => window.clearInterval(id)
  }

  return { start, command }
}
