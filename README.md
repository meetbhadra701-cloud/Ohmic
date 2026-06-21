# Simulated Multi-Agent Self-Healing Microgrid

Portfolio simulation. Not real hardware. See `00_PROJECT_EXPLAINER.md`.

- Backend (Claude Code): `backend/`  + shared `CONTRACTS/`
- Frontend (Codex): `frontend/`
- Knowledge base: `vault/` (open in Obsidian)

## Run The Demo

Prerequisites:

- macOS with Homebrew
- Python 3.14
- Node.js and npm

Install the backend once:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
brew install mosquitto
```

Start the backend simulator and WebSocket server:

```bash
make run
```

In a second terminal, install and run the frontend:

```bash
cd frontend
npm install
VITE_OHMIC_STREAM=real npm run dev -- --host 127.0.0.1
```

Open the Vite URL printed by the frontend, usually `http://127.0.0.1:5173/`.
Use **Kill Solar** to trigger the self-healing path: PV drops offline, the grid
enters CRITICAL mode, the battery grid-forms to critical load, non-critical load
sheds, and **Restore Solar** returns the system to NORMAL.

## Mock Frontend

The frontend defaults to a contract-shaped mock stream when
`VITE_OHMIC_STREAM` is omitted:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

## Verification

Run the backend checks:

```bash
make test
make check-all
```

Run frontend checks:

```bash
cd frontend
npm run build
npm run lint
```
