# Codex Frontend Dashboard Report

Date: 2026-06-21
Owner: Codex
Status: Mock-mode frontend complete; real WebSocket verification pending Claude Step 6.

## What Exists

- `frontend/` is a Vite + React + TypeScript app.
- It renders a React Three Fiber 3D microgrid scene with:
  - `PV_01` solar node
  - `BESS_01` battery node
  - `LOAD_CAMPUS` building/load node
  - `GRID_OP` operator hub
  - animated market flow lines
- It includes dashboard panels for:
  - clearing price
  - solar output
  - battery SoC/mode/flow
  - load served/shed
  - forecast vs actual demand chart
  - feeder loading, curtailed kW, unmet kW
  - alert banner
- It has a low-power mode toggle that defaults on for the 2017 MacBook Air target.
- It has `Kill Solar` and `Restore Solar` buttons using the contract command shape:

```json
{ "type": "chaos", "target": "PV_01", "action": "kill" }
```

```json
{ "type": "chaos", "target": "PV_01", "action": "restore" }
```

## Runtime Modes

Default mock stream:

```bash
cd /Users/meetbhadra/Projects/microgrid/frontend
npm run dev -- --host 127.0.0.1
```

Real WebSocket mode after Claude ships Step 6:

```bash
cd /Users/meetbhadra/Projects/microgrid/frontend
VITE_OHMIC_STREAM=real npm run dev -- --host 127.0.0.1
```

The real socket URL defaults to `ws://localhost:8765`. Override it with:

```bash
VITE_OHMIC_WS_URL=ws://localhost:8765
```

## Verification Completed

- `npm run build` passed.
- `npm run lint` passed.
- Browser render verified at `http://127.0.0.1:5173/`.
- Canvas was nonblank.
- Mock `Kill Solar` flipped the dashboard to `CRITICAL`.
- Mock `Restore Solar` returned the dashboard to `ALL_CLEAR` / `NORMAL`.
- Narrow viewport layout was checked.

## Remaining Dependency

Claude still needs to ship the WebSocket server. Once it exists, Codex should verify:

- live server sends the exact `CONTRACTS/websocket_api.md` frame
- `nodes` is the object keyed by node id
- alerts appear in the same frame as `mode` changes
- frontend commands are relayed onto `chaos/command`
- real frames drive the same UI behavior as the mock stream

