# AquaSafe Web Backend

Django/DRF backend for the AquaSafe aquaculture platform. The ESP32 firmware is
independent and lives under `firmware/esp32`.

See [ROADMAP.md](ROADMAP.md) for the phased delivery plan.

## Current status

Phases 1, 2 and 4 are complete. Phase 3 live-service validation and Phase 6
frontend integration are in progress:

- Django project with split development, production and test settings
- Custom email-based user model, JWT authentication and role groups
- camelCase API boundary, structured errors, request IDs and health endpoints
- OpenAPI documentation with drf-spectacular
- Farms, ponds, memberships and feeding records with farm-scoped authorization
- Device, sensor and actuator registry
- Sensor readings with provenance, deduplication and history queries
- Optional turbidity in NTU (`turbidityNtu` / `turbidity_ntu`, `0–1000`) and water
  level consistently stored as a percentage (`0–100`)
- Alert rules with duplicate-safe active-alert evaluation
- Dashboard summary and idempotent `/sync/bootstrap` and `/sync/import`
- Device provisioning, one-time claim, encrypted MQTT and command secrets
  (`mqttPassword` and `commandSecret` are returned once; they must differ)
- Mosquitto username/password auth, per-device ACL generation and credential sync
- MQTT ingress worker for telemetry, heartbeat, events, status and acknowledgements
- Signed, expiring device commands with command status reporting
- Signed telemetry envelopes using the device command secret
- Device configuration publishing with versioned acknowledgements and firmware
  application/persistence
- Email notification outbox and disabled-by-default delivery task for alerts
- Authenticated farm WebSocket stream and Celery expiry/stale-device tasks
- ESP32 firmware foundation with offline safety, mock sensors, local automation,
  MQTT adapters, provisioning portal, local status/manual controls, command
  verification and host tests
- Phase 4 simulation runs, live simulation state, history APIs, compatibility alias
  and development-only legacy MQTT bridge
- React API client, localStorage fallback and one-time local-record import
- Embedded live pond visualization using a `postMessage` bridge and five-second
  REST polling; WebSocket delivery is optional when Redis is available
- API tests for auth, farms, devices, telemetry, alerts, notifications, sync,
  commands, simulations and MQTT handlers

Live Mosquitto/Redis/Celery integration, target firmware compilation, flashing,
physical hardware validation, calibrated analog sensors, browser-based visual
tests, frontend offline mutation queueing and the ecosystem modules remain
outstanding. REST polling keeps the live pond view usable when Redis is absent.

## Requirements

- Python 3.13+
- `uv`
- PostgreSQL
- Redis for Channels/Celery
- Eclipse Mosquitto for MQTT
- Docker and Docker Compose (recommended for local infrastructure)

On this development machine PostgreSQL and `uv` are available. Redis, Mosquitto
and Docker are not currently installed; broker-dependent tests are skipped until
those services are available.

## Quick start

```bash
cd backend

cp .env.example .env
# Edit .env. At minimum set DJANGO_SECRET_KEY and a MQTT_PASSWORD.
# Generate a device-secret encryption key:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Using the host PostgreSQL instance:
createdb aquasafe

make setup
make run
```

The API is available at `http://localhost:8000/api/v1/`.
Swagger UI is at `http://localhost:8000/api/docs/`.

### Using Docker Compose PostgreSQL

`docker-compose.yml` exposes PostgreSQL on port `5433` to avoid conflicting with
a host PostgreSQL instance.

```bash
make compose-up
# Set in .env:
# DATABASE_URL=postgres://aquasafe:aquasafe@localhost:5433/aquasafe
make migrate
```

### Mosquitto credentials

The broker requires a generated password file:

```bash
make broker-init
```

This writes `mosquitto/config/passwd`, which is ignored by git. The default ACLs
are in `mosquitto/config/acl`. After claiming devices, synchronise per-device
credentials and ACLs:

```bash
make broker-credentials
```

See [docs/mqtt.md](docs/mqtt.md) for topics, provisioning, ACLs, worker operation
and TLS configuration.

## Tests

```bash
make test
```

Tests use PostgreSQL database `aquasafe_test` and in-memory Channels/Celery
adapters. A live Mosquitto broker is not required for the current tests.

Firmware host tests:

```bash
make firmware-test
```

## Useful commands

```bash
make run            # ASGI server on :8000
make migrate        # apply migrations
make makemigrations # create migrations
make seed           # seed role groups and permissions
make lint           # Ruff
make format         # Ruff formatter
make mqtt-worker     # long-running MQTT ingress worker
make broker-credentials  # write per-device ACLs and broker passwords
make firmware-test   # compile and run portable firmware core tests
uv run python manage.py run_simulation_bridge  # development-only legacy demo bridge
make compose-up      # PostgreSQL, Redis, Mosquitto
make compose-down
```

## Authentication

- Register: `POST /api/v1/auth/register/`
- Login: `POST /api/v1/auth/login/`
- Refresh: `POST /api/v1/auth/refresh/`
- Logout: `POST /api/v1/auth/logout/`
- Profile: `GET/PATCH /api/v1/users/me/`
- Roles: `GET /api/v1/roles/` (admin)
- Permissions: `GET /api/v1/permissions/` (admin)

Use `Authorization: Bearer <access>` for authenticated requests.

## Core domain APIs

- Farms: `GET/POST /api/v1/farms/`, `GET/PATCH/DELETE /api/v1/farms/{id}/`
- Ponds: `GET/POST /api/v1/ponds/`, filter with `?farmId=`
- Feeding: `GET/POST /api/v1/feedings/`, filter with `?pondId=`
- Devices: `GET/POST /api/v1/devices/`, filter with `?farmId=` and `?pondId=`
- Sensors/actuators: `GET/POST /api/v1/sensors/` and `/api/v1/actuators/`
- Readings: `GET/POST /api/v1/readings/`, `GET /api/v1/readings/latest/`
  (`level` is percent; optional `turbidityNtu` is NTU)
- Alert rules: `GET/POST /api/v1/alert-rules/`
- Alerts: `GET /api/v1/alerts/`, acknowledge/resolve actions
- Dashboard: `GET /api/v1/dashboard/summary/`
- Sync: `GET /api/v1/sync/bootstrap/`, `POST /api/v1/sync/import/`
- Provisioning: `POST /api/v1/devices/{id}/provision/`, public `POST /api/v1/devices/claim/`
- Device config: `POST /api/v1/devices/{id}/config/`
- Commands: `GET/POST /api/v1/commands/`, `GET /api/v1/commands/{id}/`
- Simulations: `GET/POST /api/v1/simulations/`, `/api/simulations` compatibility
- Simulation state: `GET/POST /api/v1/simulations/state/`
- WebSocket: `ws/farms/{farm_id}/` with JWT access token authentication

Readings accept `source` values `physical`, `simulation`, `manual` or `import`.
Client-generated IDs use `clientId` for idempotent imports and duplicate rejection.
See [docs/simulations.md](docs/simulations.md) for the frontend contract, embedded
visualization bridge, live-state degradation and legacy `fish_pond-live.html`
normalisation. See [docs/mqtt.md](docs/mqtt.md) for telemetry payload fields,
including optional turbidity.

## Frontend integration

The React app is in `frontend/fishlink`. It uses the backend by default at
`http://localhost:8000/api/v1`; override it with `REACT_APP_API_URL`.

```bash
cd frontend/fishlink
npm install
REACT_APP_API_URL=http://localhost:8000/api/v1 npm start
```

`npm run build` and `npx tsc --noEmit` are the current verification commands.
When the API is unavailable, the app retains its localStorage guest mode. Local
records can be imported once from the profile page; imports are idempotent and
the backend warns that legacy values recorded in metres cannot be converted
without pond depth. Marketplace and community screens remain local-only.

## Project structure

```text
config/          settings, ASGI, WSGI, Celery, root URLs
apps/            Django domain apps
integrations/    MQTT and external integrations
firmware/esp32/  independent Arduino/PlatformIO firmware
mosquitto/       broker configuration and runtime data
docs/            architecture, API, MQTT and deployment documentation
tests/           unit and API tests
```

## Security notes

- `.env`, generated broker passwords and device secrets are ignored by git.
- The production settings require a real `DJANGO_SECRET_KEY` and
  `DEVICE_SECRET_ENCRYPTION_KEY`.
- Alert email delivery stays disabled until a real provider is configured. No
  message is marked sent unless Django's email backend accepts it.
- Payments and external SMS/WhatsApp integrations are not implemented as
  successful integrations. Provider abstractions will remain disabled until
  real credentials are supplied.
- The public HiveMQ topic from the earlier simulation demo is used only by the
  explicitly enabled, development-only legacy bridge. It is not production
  infrastructure and must never carry device credentials.
