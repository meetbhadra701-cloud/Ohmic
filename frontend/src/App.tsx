import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text } from '@react-three/drei'
import { Activity, BatteryCharging, CircleAlert, Gauge, RadioTower, Zap } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { BufferGeometry, Group, Mesh, MeshBasicMaterial } from 'three'
import './App.css'
import { createStreamClient } from './stream'
import { useTelemetryStore } from './store'
import type { MarketFlow, NodeMap, TelemetryFrame } from './types'

const nodePositions: Record<keyof NodeMap, [number, number, number]> = {
  PV_01: [-2.65, 0, -0.65],
  BESS_01: [0, 0, 1.1],
  LOAD_CAMPUS: [2.75, 0, -0.6],
}

const kw = (value: number) => `${value.toFixed(1)} kW`
const price = (value: number | null) => (value === null ? 'n/a' : `$${value.toFixed(3)}`)

function FlowLine({ flow, lowPower }: { flow: MarketFlow; lowPower: boolean }) {
  const mesh = useRef<Mesh<BufferGeometry, MeshBasicMaterial>>(null)
  const from = nodePositions[flow.from]
  const to = nodePositions[flow.to]
  const midX = (from[0] + to[0]) / 2
  const midZ = (from[2] + to[2]) / 2
  const length = Math.hypot(to[0] - from[0], to[2] - from[2])
  const angle = Math.atan2(to[2] - from[2], to[0] - from[0])
  const thickness = Math.min(0.18, 0.045 + flow.kw / 620)

  useFrame(({ clock }) => {
    if (!mesh.current || lowPower) return
    mesh.current.material.opacity = 0.42 + Math.sin(clock.elapsedTime * 4 + flow.kw / 10) * 0.18
  })

  return (
    <mesh ref={mesh} position={[midX, 0.18, midZ]} rotation={[0, -angle, Math.PI / 2]}>
      <cylinderGeometry args={[thickness, thickness, length, lowPower ? 8 : 16]} />
      <meshBasicMaterial color={flow.from === 'PV_01' ? '#f7c948' : '#45d3a2'} transparent opacity={0.58} />
    </mesh>
  )
}

function SolarNode({ frame, lowPower }: { frame: TelemetryFrame; lowPower: boolean }) {
  const group = useRef<Group>(null)
  const solar = frame.nodes.PV_01
  const intensity = solar.alive ? Math.max(0.28, solar.output_kw / 90) : 0.08

  useFrame(({ clock }) => {
    if (!group.current || lowPower) return
    group.current.rotation.y = Math.sin(clock.elapsedTime * 0.5) * 0.08
  })

  return (
    <group ref={group} position={nodePositions.PV_01}>
      <mesh position={[0, 0.46, 0]} rotation={[-0.55, 0, 0]}>
        <boxGeometry args={[1.7, 0.08, 1]} />
        <meshStandardMaterial color={solar.alive ? '#164e63' : '#30343b'} emissive={solar.alive ? '#facc15' : '#111827'} emissiveIntensity={intensity} />
      </mesh>
      <mesh position={[0, 0.13, 0]}>
        <cylinderGeometry args={[0.05, 0.05, 0.65, 10]} />
        <meshStandardMaterial color="#78909c" />
      </mesh>
      <mesh position={[0, -0.05, 0]}>
        <boxGeometry args={[1.2, 0.1, 0.95]} />
        <meshStandardMaterial color="#17212b" />
      </mesh>
      {!lowPower && solar.alive ? (
        <pointLight color="#facc15" intensity={solar.output_kw / 42} distance={4.4} position={[0, 1.2, 0]} />
      ) : null}
      <Text position={[0, 1.25, 0]} fontSize={0.22} color="#f8fafc" anchorX="center">
        PV_01 {solar.alive ? kw(solar.output_kw) : 'OFFLINE'}
      </Text>
    </group>
  )
}

function BatteryNode({ frame }: { frame: TelemetryFrame }) {
  const battery = frame.nodes.BESS_01
  const fillHeight = 0.18 + battery.soc * 1.15
  const critical = battery.mode === 'grid_forming'

  return (
    <group position={nodePositions.BESS_01}>
      <mesh position={[0, 0.62, 0]}>
        <boxGeometry args={[0.9, 1.45, 0.8]} />
        <meshStandardMaterial color="#101820" metalness={0.35} roughness={0.48} />
      </mesh>
      <mesh position={[0, 0.12 + fillHeight / 2, 0.03]}>
        <boxGeometry args={[0.72, fillHeight, 0.72]} />
        <meshStandardMaterial color={critical ? '#ff6b4a' : '#45d3a2'} emissive={critical ? '#7f1d1d' : '#064e3b'} emissiveIntensity={0.45} />
      </mesh>
      <mesh position={[0, 1.42, 0]}>
        <boxGeometry args={[0.45, 0.16, 0.5]} />
        <meshStandardMaterial color="#cbd5e1" />
      </mesh>
      <Text position={[0, 1.72, 0]} fontSize={0.21} color="#f8fafc" anchorX="center">
        BESS {battery.soc_percent.toFixed(1)}%
      </Text>
      <Text position={[0, -0.34, 0]} fontSize={0.16} color={critical ? '#ffb199' : '#b7f7df'} anchorX="center">
        {battery.mode} / {kw(battery.flow_kw)}
      </Text>
    </group>
  )
}

function LoadNode({ frame }: { frame: TelemetryFrame }) {
  const load = frame.nodes.LOAD_CAMPUS
  const shedRatio = load.demand_kw === 0 ? 0 : load.shed_kw / load.demand_kw
  const height = 0.8 + Math.min(0.95, load.served_kw / 125)

  return (
    <group position={nodePositions.LOAD_CAMPUS}>
      <mesh position={[0, height / 2, 0]}>
        <boxGeometry args={[1.25, height, 1.05]} />
        <meshStandardMaterial color={shedRatio > 0 ? '#5c1f1f' : '#243447'} emissive={shedRatio > 0 ? '#7f1d1d' : '#0f2f35'} emissiveIntensity={0.34} />
      </mesh>
      <mesh position={[-0.32, height + 0.18, 0]}>
        <boxGeometry args={[0.32, 0.36, 0.38]} />
        <meshStandardMaterial color="#3c4f63" />
      </mesh>
      <mesh position={[0.28, height + 0.13, 0]}>
        <boxGeometry args={[0.28, 0.26, 0.34]} />
        <meshStandardMaterial color="#3c4f63" />
      </mesh>
      <Text position={[0, height + 0.62, 0]} fontSize={0.21} color="#f8fafc" anchorX="center">
        LOAD {kw(load.served_kw)}
      </Text>
      <Text position={[0, -0.3, 0]} fontSize={0.16} color={shedRatio > 0 ? '#ffb199' : '#cbd5e1'} anchorX="center">
        shed {kw(load.shed_kw)}
      </Text>
    </group>
  )
}

function OperatorHub({ frame }: { frame: TelemetryFrame }) {
  const critical = frame.mode === 'CRITICAL'

  return (
    <group position={[0, 0, -1.8]}>
      <mesh position={[0, 0.45, 0]}>
        <cylinderGeometry args={[0.62, 0.82, 0.9, 8]} />
        <meshStandardMaterial color={critical ? '#7f1d1d' : '#183b46'} emissive={critical ? '#ef4444' : '#0e7490'} emissiveIntensity={0.5} />
      </mesh>
      <mesh position={[0, 1.12, 0]}>
        <sphereGeometry args={[0.25, 16, 10]} />
        <meshStandardMaterial color={critical ? '#ff6b4a' : '#67e8f9'} emissive={critical ? '#ef4444' : '#06b6d4'} emissiveIntensity={0.65} />
      </mesh>
      <Text position={[0, 1.55, 0]} fontSize={0.18} color="#f8fafc" anchorX="center">
        GRID_OP {frame.mode}
      </Text>
    </group>
  )
}

function MicrogridScene({ frame, lowPower }: { frame: TelemetryFrame; lowPower: boolean }) {
  return (
    <Canvas camera={{ position: [0, 5.2, 7.6], fov: 48 }} dpr={lowPower ? [1, 1.25] : [1, 1.75]}>
      <color attach="background" args={['#071013']} />
      <ambientLight intensity={0.48} />
      <directionalLight position={[2, 5, 4]} intensity={1.4} />
      {!lowPower ? <pointLight position={[0, 2.4, -1.2]} intensity={2.1} color="#2dd4bf" /> : null}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <planeGeometry args={[9, 5.6, 1, 1]} />
        <meshStandardMaterial color="#0b171a" roughness={0.95} />
      </mesh>
      <gridHelper args={[9, 18, '#1e5960', '#102a2f']} position={[0, 0.01, 0]} />
      {frame.market.flows.map((flow) => (
        <FlowLine key={`${flow.from}-${flow.to}-${flow.kw}`} flow={flow} lowPower={lowPower} />
      ))}
      <SolarNode frame={frame} lowPower={lowPower} />
      <BatteryNode frame={frame} />
      <LoadNode frame={frame} />
      <OperatorHub frame={frame} />
      <OrbitControls enablePan={false} minDistance={5.2} maxDistance={9} maxPolarAngle={Math.PI / 2.2} />
    </Canvas>
  )
}

function MetricCard({ label, value, detail, tone = 'normal' }: { label: string; value: string; detail: string; tone?: 'normal' | 'critical' }) {
  return (
    <section className={`metric-card ${tone}`} aria-label={label}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </section>
  )
}

function Dashboard() {
  const frame = useTelemetryStore((state) => state.frame)
  const history = useTelemetryStore((state) => state.history)
  const status = useTelemetryStore((state) => state.status)
  const lowPower = useTelemetryStore((state) => state.lowPower)
  const lastMessage = useTelemetryStore((state) => state.lastMessage)
  const setFrame = useTelemetryStore((state) => state.setFrame)
  const setStatus = useTelemetryStore((state) => state.setStatus)
  const setLowPower = useTelemetryStore((state) => state.setLowPower)
  const client = useMemo(() => createStreamClient(), [])

  useEffect(() => {
    setStatus(client.isMock ? 'mock' : 'connecting', client.isMock ? 'Mock stream active' : `Connecting to ${client.url}`)
    return client.connect(
      (nextFrame) => {
        setFrame(nextFrame)
        setStatus(client.isMock ? 'mock' : 'live', client.isMock ? 'Mock stream active' : `Live stream ${client.url}`)
      },
      (message) => setStatus(message.includes('error') ? 'error' : 'offline', message),
    )
  }, [client, setFrame, setStatus])

  if (!frame) {
    return (
      <main className="loading-shell" id="main-content">
        <p>Waiting for the first telemetry frame...</p>
      </main>
    )
  }

  const solar = frame.nodes.PV_01
  const battery = frame.nodes.BESS_01
  const load = frame.nodes.LOAD_CAMPUS
  const feeder = frame.market.per_line_flow_kw.FEEDER_1 ?? 0
  const topAlert = frame.alerts[0]
  const ridgeCondition = frame.forecast.cond === null ? 'warming' : frame.forecast.cond.toFixed(1)
  const demandSummary = `Actual demand ${kw(frame.forecast.actual_demand_kw)}. Forecast ${kw(frame.forecast.predicted_demand_kw)}.`

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to dashboard</a>
      <header className="app-header">
        <div>
          <p className="eyebrow">Simulated microgrid control room</p>
          <h1>Ohmic</h1>
        </div>
        <div className="header-status" aria-live="polite">
          <span className={`status-dot ${frame.mode.toLowerCase()}`} aria-hidden="true" />
          <span>{frame.mode}</span>
          <span>Tick {frame.tick}</span>
          <span>{frame.sim_time}</span>
        </div>
      </header>

      <main className="dashboard" id="main-content">
        <section className="scene-panel" aria-label="3D microgrid visualization">
          <MicrogridScene frame={frame} lowPower={lowPower} />
          <div className={`alert-banner ${frame.mode.toLowerCase()}`} role="status" aria-live="polite">
            <CircleAlert aria-hidden="true" size={20} />
            <span>{topAlert ? `${topAlert.level}: ${topAlert.detail}` : 'NORMAL: Market and physical constraints are steady'}</span>
          </div>
        </section>

        <aside className="side-panel" aria-label="Microgrid controls and telemetry">
          <section className="control-strip" aria-label="Simulation controls">
            <button type="button" className="danger-button" onClick={() => client.sendChaos('kill')}>
              Kill Solar
            </button>
            <button type="button" className="restore-button" onClick={() => client.sendChaos('restore')}>
              Restore Solar
            </button>
            <label className="toggle">
              <input type="checkbox" checked={lowPower} onChange={(event) => setLowPower(event.target.checked)} />
              Low-power mode
            </label>
          </section>

          <div className="metric-grid">
            <MetricCard label="Clearing price" value={price(frame.market.clearing_price_usd_kwh)} detail="USD/kWh" />
            <MetricCard label="Solar output" value={solar.alive ? kw(solar.output_kw) : 'offline'} detail={solar.health} tone={solar.alive ? 'normal' : 'critical'} />
            <MetricCard label="Battery" value={`${battery.soc_percent.toFixed(1)}%`} detail={`${battery.mode}, ${kw(battery.flow_kw)}`} tone={battery.mode === 'grid_forming' ? 'critical' : 'normal'} />
            <MetricCard label="Load served" value={kw(load.served_kw)} detail={`${kw(load.shed_kw)} shed`} tone={load.shed_kw > 0 ? 'critical' : 'normal'} />
          </div>

          <section className="chart-panel" aria-label="Forecast versus actual demand">
            <div className="panel-title">
              <Activity aria-hidden="true" size={18} />
              <h2>Demand Forecast</h2>
            </div>
            <p className="sr-only">{demandSummary}</p>
            <ResponsiveContainer width="100%" height={170}>
              <AreaChart data={history} margin={{ top: 12, right: 4, bottom: 0, left: -18 }}>
                <defs>
                  <linearGradient id="actual" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#45d3a2" stopOpacity={0.7} />
                    <stop offset="95%" stopColor="#45d3a2" stopOpacity={0.04} />
                  </linearGradient>
                  <linearGradient id="predicted" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#f7c948" stopOpacity={0.55} />
                    <stop offset="95%" stopColor="#f7c948" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1d3a3f" strokeDasharray="3 3" />
                <XAxis dataKey="sim_time" tick={{ fill: '#90a4ae', fontSize: 11 }} minTickGap={24} />
                <YAxis tick={{ fill: '#90a4ae', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#08171a', border: '1px solid #244a50', color: '#e8f4f5' }} />
                <Area type="monotone" dataKey="actual" stroke="#45d3a2" fill="url(#actual)" name="Actual kW" />
                <Area type="monotone" dataKey="predicted" stroke="#f7c948" fill="url(#predicted)" name="Forecast kW" />
              </AreaChart>
            </ResponsiveContainer>
          </section>

          <section className="systems-panel" aria-label="System diagnostics">
            <div className="panel-title">
              <Gauge aria-hidden="true" size={18} />
              <h2>Physical Limits</h2>
            </div>
            <dl>
              <div>
                <dt><RadioTower aria-hidden="true" size={16} /> FEEDER_1</dt>
                <dd>{kw(feeder)} live flow</dd>
              </div>
              <div>
                <dt><Zap aria-hidden="true" size={16} /> Curtailed</dt>
                <dd>{kw(frame.market.curtailed_kw)}</dd>
              </div>
              <div>
                <dt><BatteryCharging aria-hidden="true" size={16} /> Unmet</dt>
                <dd>{kw(frame.market.unmet_kw + battery.unmet_kw)}</dd>
              </div>
            </dl>
          </section>

          <p className="connection-note" aria-live="polite">
            Stream: {status} / {client.url}. Ridge condition: {ridgeCondition}. {lastMessage}
          </p>
        </aside>
      </main>
    </>
  )
}

export default function App() {
  return <Dashboard />
}
