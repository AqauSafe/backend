# AquaSafe Web Backend

Django/DRF backend for the AquaSafe aquaculture platform. The ESP32 firmware is
independent and lives under `firmware/esp32`.

See [ROADMAP.md](ROADMAP.md) for the phased delivery plan.

## Current status

Phases 1 and 2 are implemented:

- Django project with split development, production and test settings
- Custom email-based user model, JWT authentication and role groups
- camelCase API boundary, structured errors, request IDs and health endpoints
- OpenAPI documentation with drf-spectacular
- Farms, ponds, memberships and feeding records with farm-scoped authorization
- Device, sensor and actuator registry
- Sensor readings with provenance, deduplication and history queries
- Alert rules with duplicate-safe active-alert evaluation
- Dashboard summary and idempotent `/sync/bootstrap` and `/sync/import`
- PostgreSQL, Celery, Channels and Mosquitto configuration
- API tests for auth, farms, devices, telemetry, alerts and sync

Hardware provisioning, live MQTT ingestion, simulation APIs and the ecosystem
modules are implemented in later roadmap phases.

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
are in `mosquitto/config/acl`; per-device credentials and topic ACL synchronisation
land in Phase 3.

## Tests

```bash
make test
```

Tests use PostgreSQL database `aquasafe_test` and in-memory Channels/Celery
adapters. A live Mosquitto broker is not required for the current tests.

## Useful commands

```bash
make run            # ASGI server on :8000
make migrate        # apply migrations
make makemigrations # create migrations
make seed           # seed role groups and permissions
make lint           # Ruff
make format         # Ruff formatter
make compose-up     # PostgreSQL, Redis, Mosquitto
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
- Alert rules: `GET/POST /api/v1/alert-rules/`
- Alerts: `GET /api/v1/alerts/`, acknowledge/resolve actions
- Dashboard: `GET /api/v1/dashboard/summary/`
- Sync: `GET /api/v1/sync/bootstrap/`, `POST /api/v1/sync/import/`

Readings accept `source` values `physical`, `simulation`, `manual` or `import`.
Client-generated IDs use `clientId` for idempotent imports and duplicate rejection.

## Project structure

```text
config/          settings, ASGI, WSGI, Celery, root URLs
apps/            Django domain apps
integrations/    MQTT and external integrations
firmware/esp32/  independent Arduino/PlatformIO firmware
mosquitto/       broker configuration and runtime data
docs/            architecture, API and deployment documentation
tests/           unit and API tests
```

## Security notes

- `.env`, generated broker passwords and device secrets are ignored by git.
- The production settings require a real `DJANGO_SECRET_KEY` and
  `DEVICE_SECRET_ENCRYPTION_KEY`.
- Payments and external SMS/WhatsApp/email delivery are not implemented as
  successful integrations. Provider abstractions will remain disabled until
  real credentials are supplied.
- The public HiveMQ credentials/topic from the earlier simulation demo are not
  used by this backend and should not be treated as production infrastructure.
