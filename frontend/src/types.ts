export type GridMode = 'NORMAL' | 'CRITICAL'
export type Health = 'nominal' | 'degraded' | 'fault'
export type AlertLevel = 'CRITICAL' | 'ALL_CLEAR'
export type ChaosAction = 'kill' | 'restore'

export type SolarNode = {
  type: 'solar'
  output_kw: number
  alive: boolean
  health: Health
}

export type BatteryNode = {
  type: 'battery'
  soc: number
  soc_percent: number
  flow_kw: number
  max_discharge_kw: number
  mode: 'market' | 'grid_forming'
  ask_price_usd_kwh: number | null
  unmet_kw: number
  health: Health
}

export type LoadNode = {
  type: 'load'
  demand_kw: number
  critical_kw: number
  served_kw: number
  shed_kw: number
  health: Health
}

export type NodeMap = {
  PV_01: SolarNode
  BESS_01: BatteryNode
  LOAD_CAMPUS: LoadNode
}

export type MarketFlow = {
  from: keyof NodeMap
  to: keyof NodeMap
  kw: number
  curtailed_kw: number
}

export type Alert = {
  level: AlertLevel
  type: 'SOLAR_LOSS' | string
  detail: string
  tick: number
}

export type TelemetryFrame = {
  schema_version: 1
  tick: number
  sim_time: string
  day_phase: number
  mode: GridMode
  nodes: NodeMap
  market: {
    clearing_price_usd_kwh: number | null
    flows: MarketFlow[]
    unmet_kw: number
    surplus_kw: number
    curtailed_kw: number
    per_line_flow_kw: Record<string, number>
  }
  forecast: {
    predicted_demand_kw: number
    horizon_ticks: number
    actual_demand_kw: number
    cond: number | null
    reanchor_count: number
    warm: boolean
  }
  alerts: Alert[]
}

export type ChaosCommand = {
  type: 'chaos'
  target: 'PV_01'
  action: ChaosAction
}

export type StreamStatus = 'mock' | 'connecting' | 'live' | 'offline' | 'error'

export type DemandPoint = {
  tick: number
  sim_time: string
  actual: number
  predicted: number
}
