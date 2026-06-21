PYTHON := .venv/bin/python

.PHONY: run test check-all check-tick check-market check-heal check-ws smoke

## One-command demo: start broker (if needed) + sim + WebSocket server.
run:
	$(PYTHON) backend/main.py

## Run all unit tests.
test:
	$(PYTHON) -m pytest backend/tests/ -q

## Run every gate check in sequence.
check-all: smoke check-tick check-market check-heal check-ws

smoke:
	$(PYTHON) backend/scripts/smoke_mqtt.py

check-tick:
	$(PYTHON) backend/scripts/check_tick.py

check-market:
	$(PYTHON) backend/scripts/check_market.py

check-heal:
	$(PYTHON) backend/scripts/check_heal.py

check-ws:
	$(PYTHON) backend/scripts/check_ws.py
