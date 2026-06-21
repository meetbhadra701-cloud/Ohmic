# Claude Code — Build Log (Claude writes; Codex does not edit)

<!-- Newest entries on top. Template:

## [date-time] <title>
- What I did:
- Files touched (backend/ or CONTRACTS/ only):
- Decisions/assumptions (+ defaults):
- Open questions / risks for the human:
- Next step:
-->

## [2026-06-20] CONTRACTS published v1
- What I did: Authored the three contract files that Codex (frontend) was blocked on, and added the HTTPS git remote (SSH currently fails with publickey).
- Files touched (backend/ or CONTRACTS/ only): `CONTRACTS/mqtt_topics.md`, `CONTRACTS/message_schemas.md`, `CONTRACTS/websocket_api.md`.
- Decisions/assumptions (+ defaults): Froze four spec gaps (see `vault/Decisions/0001-contract-spec-gaps.md`): (1) uniform clearing price = last matched ask price; (2) curtailed trades settle on delivered kW at cleared price; (3) sign convention generation/discharge +, load/charge −; (4) heartbeat clears after ≥2 consecutive good beats (anti-flap). Dedicated `node/<id>/heartbeat` topic separate from state. WebSocket frame is a render-complete superset at `ws://localhost:8765`, one frame per tick, with a client→server `chaos` command for the Kill-Solar control.
- Open questions / risks for the human: Python 3.14.2 on the Intel Air — numpy/scikit-learn/paho wheels resolve, but to de-risk, the ridge re-anchor will use a numpy closed-form fallback (sklearn optional). Mosquitto not yet installed (will `brew install` in Step 0.5).
- Next step: Backend skeleton, requirements.txt, venv, install + start Mosquitto, MQTT smoke test.
