PYTHON ?= uv run python
PYTEST ?= uv run pytest
RUFF ?= uv run ruff

.PHONY: help setup install migrate makemigrations seed run test lint format check compose-up compose-down broker-init broker-credentials mqtt-worker firmware-test

help:
	@echo "AquaSafe backend targets:"
	@echo "  make setup         Install dependencies, migrate, seed roles"
	@echo "  make run           Run the ASGI development server on :8000"
	@echo "  make test          Run the test suite"
	@echo "  make lint          Run Ruff"
	@echo "  make format        Format with Ruff"
	@echo "  make compose-up    Start PostgreSQL, Redis and Mosquitto"
	@echo "  make broker-init   Generate the Mosquitto password file"
	@echo "  make broker-credentials  Sync per-device ACLs and broker passwords"
	@echo "  make mqtt-worker   Run the MQTT ingress worker"
	@echo "  make firmware-test Run host firmware core tests"
	@echo "  make migrate       Apply database migrations"
	@echo "  make seed          Seed role groups and permissions"

setup: install migrate seed

install:
	uv sync

migrate:
	$(PYTHON) manage.py migrate

makemigrations:
	$(PYTHON) manage.py makemigrations

seed:
	$(PYTHON) manage.py seed_roles

run:
	uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application

test:
	$(PYTEST)

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

check: lint test

compose-up:
	docker compose up -d postgres redis mosquitto

compose-down:
	docker compose down

broker-init:
	@test -f .env && . ./.env; \
	docker compose run --rm --entrypoint mosquitto_passwd mosquitto \
		-c -b /mosquitto/config/passwd "$${MQTT_USERNAME:-aquasafe-backend}" \
		"$${MQTT_PASSWORD:-change-me}"

broker-credentials:
	$(PYTHON) manage.py sync_mqtt_credentials

mqtt-worker:
	$(PYTHON) manage.py run_mqtt_worker

firmware-test:
	cd firmware/esp32 && ./test/run_host_tests.sh
