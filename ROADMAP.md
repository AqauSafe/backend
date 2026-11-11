# AquaSafe Backend Roadmap

**Project:** AquaSafe — smart aquaculture management ecosystem  
**Team:** Tech Sharks — NIMASA National Innovation Hackathon  
**Document status:** Active  
**Last updated:** 2026-11-11

---

## 1. Purpose

This roadmap records the agreed architecture, delivery phases, acceptance criteria and known constraints for the AquaSafe backend. It is the source of truth for implementation order and scope.

AquaSafe consists of two independently deployable systems:

1. **AquaSafe Web Backend** — Django/DRF/Channels/Celery/PostgreSQL/Redis.
2. **AquaSafe Hardware Backend** — ESP32 Arduino/PlatformIO firmware under `backend/firmware/esp32`.

Eclipse Mosquitto is the standard MQTT broker in development and production. The two systems communicate through MQTT and authenticated HTTP APIs, but each must remain useful independently.

---

## 2. Confirmed technology decisions

| Area | Decision |
|---|---|
| Language | Python 3.13+ |
| Web framework | Django 5.2 LTS |
| API | Django REST Framework |
| Database | PostgreSQL |
| ORM | Django ORM |
| Realtime | Django Channels over ASGI |
| Background jobs | Celery + Celery Beat |
| Broker/cache | Redis |
| MQTT | Eclipse Mosquitto |
| API documentation | drf-spectacular |
| Authentication | SimpleJWT (access/refresh rotation, blacklist) |
| Password hashing | Argon2id |
| Firmware | Arduino framework, PlatformIO-compatible `.ino`, modular C++ |
| Python environment | `uv` |
| Linting | Ruff |
| Testing | pytest + pytest-django, DRF API tests, Channels tests |
| Local infrastructure | Docker Compose (PostgreSQL, Redis, Mosquitto, app services) |

No Node.js backend, Fastify, Prisma or Drizzle will be introduced.

---

## 3. Repository context and constraints

### Existing state

- `backend/` previously contained only `LICENSE` and an initial commit.
- `frontend/fishlink/` is a React 18 + TypeScript app using `localStorage` (`fishlink-data-v2`) as its data store.
- `frontend/fishlink/src/App.tsx` is the mounted application.
- `frontend/fishlink/src/test1.tsx` is an unwired duplicate with an additional planning simulation.
- `frontend/fishlink/src/PondSimulation.tsx` is a placeholder integration point.
- `frontend/fish_pond-live.html` is the canonical ESP32/MQTT fish-pond simulation.
- The Velxio ESP32 project and `fishpond_flask.zip` are not in the repository.
- No physical pin map or confirmed sensor models are available.

### Compatibility constraints

- Preserve the working frontend and its current localStorage behaviour.
- Backend integration must be additive and feature-flagged.
- API serializers must support the existing frontend field names (`farmId`, `pondId`, `oxygen`, `level`, `simulationRuns`, etc.).
- Preserve the `POST /api/simulations` expectation from `test1.tsx` as a compatibility alias.
- Do not delete or rewrite the existing simulation files without explicit approval.
- Do not copy exposed Velxio credentials into source control or documentation.

### Environment constraints

- PostgreSQL 18 is available locally.
- `uv` is available; `pip` is not installed.
- Docker, Redis and Mosquitto are not currently installed on the development machine.
- MQTT integration tests are optional unless a live broker is available and will not be reported as passing otherwise.
- Firmware cannot be flashed or electrically validated here. Compilation and host-level logic tests are the maximum verifiable scope until hardware and toolchain are available.

---

## 4. Engineering principles

- Modular monolith with clear Django app boundaries.
- No unnecessary microservices.
- Offline-first: loss of internet must never disable local hardware operation.
- Device commands are authenticated, signed, timestamped, expiring, deduplicated and acknowledged.
- Local safety constraints always override remote commands.
- Every sensor and actuator is registry-driven; unsupported hardware is never assumed.
- All timestamps stored in UTC with explicit device-recorded and server-received times.
- Every mutation that matters is auditable.
- No fabricated integrations, passing tests or successful payments.
- Secrets only through environment variables; never committed.
- The web backend and firmware are independently deployable.

---

## 5. Milestone overview

| Phase | Name | Primary outcome | Status |
|---|---|---|---|
| 0 | Repository audit | Architecture and gaps documented | Complete |
| 1 | Django foundation | Runnable backend, auth, RBAC, DB, docs, tests | Complete |
| 2 | Core aquaculture domain | Farms, ponds, devices, sensors, telemetry, alerts | Complete |
| 3 | Hardware integration | Mosquitto, MQTT worker, commands, provisioning, firmware foundation | Not started |
| 4 | Simulation integration | Common telemetry model and simulation APIs | Not started |
| 5 | Application ecosystem | Marketplace, messaging, support, installations, subscriptions | Not started |
| 6 | Frontend integration | Feature-flagged API client with localStorage fallback | Not started |
| 7 | Verification and deployment | End-to-end tests, security review, deployment documentation | Not started |

Demo-critical path: **Phase 1 → Phase 2 → Phase 3 → Phase 4**. Phase 5 and Phase 6 follow without blocking the core hardware/software demonstration.

---

## 6. Phase 0 — Repository audit

**Status:** Complete

### Findings

- No existing backend implementation to preserve.
- Frontend is a functional localStorage prototype.
- Two simulation implementations exist; `fish_pond-live.html` is canonical.
- Existing MQTT demo uses a public HiveMQ topic and raw 10-bit ADC values.
- No device authentication, offline buffering, command system or firmware source exists in the repository.
- No tests, migrations, environment configuration or API documentation exist.

### Deliverables

- [x] Inspect backend and frontend repositories.
- [x] Identify frontend data contracts and simulation integration points.
- [x] Identify hardware assumptions and gaps.
- [x] Produce initial architecture assessment and implementation plan.

---

## 7. Phase 1 — Django foundation

**Goal:** A runnable, documented, tested backend skeleton with identity and access control.

### Tasks

- [x] Initialise `pyproject.toml` with pinned dependencies using `uv`.
- [x] Create Django project `config/` and split settings: `base`, `dev`, `prod`, `test`.
- [x] Add environment configuration and validated `.env.example`.
- [x] Implement custom `accounts.User` before the first migration.
- [x] Create `aquasafe` and `aquasafe_test` PostgreSQL databases.
- [x] Configure PostgreSQL and Django ORM.
- [x] Configure DRF, camelCase request/response rendering, consistent error envelope and pagination.
- [x] Configure SimpleJWT with rotation and blacklist.
- [x] Implement Argon2id password hashing.
- [x] Seed configurable roles and permissions for farmer, doctor, administrator, technician, installer and seller.
- [x] Implement registration, login, refresh, logout and current-user endpoints.
- [x] Implement permission-based access control and farm membership foundation.
- [x] Add audit log base model and mutation hooks.
- [x] Configure drf-spectacular and expose `/api/docs`.
- [x] Configure CORS, CSRF and security headers.
- [x] Add health and readiness endpoints.
- [x] Add structured logging and request IDs.
- [x] Add Ruff configuration and formatting.
- [x] Add pytest + pytest-django test harness.
- [x] Add Docker Compose definitions for PostgreSQL, Redis and Mosquitto.
- [x] Add Makefile targets for install, migrate, run, worker, broker and test.
- [x] Write initial `README.md` and API conventions documentation.

### Acceptance criteria

- `uv sync` installs the environment.
- Migrations apply cleanly to a fresh database.
- Registration, login, refresh and logout work through API tests.
- Permission checks are covered by tests.
- `/api/docs` renders.
- `ruff check` and the test suite pass.
- No secrets are committed.
- The web server starts with a single documented command.

---

## 8. Phase 2 — Core aquaculture domain

**Goal:** Persist and expose the aquaculture data model with offline-safe identifiers and provenance.

### Tasks

- [x] Implement `Farm`, `Pond`, `FarmMembership` and `Feeding`.
- [x] Implement `Device`, `Sensor` and `Actuator` registry models.
- [x] Implement `SensorReading`, `DeviceHeartbeat` and `DeviceEvent`.
- [x] Implement `AlertRule` and `Alert` lifecycle.
- [x] Implement manual reading and feeding APIs.
- [x] Implement latest-reading and historical-reading queries with pagination.
- [x] Implement dashboard summary endpoint.
- [x] Add provenance (`physical`, `simulation`, `manual`, `import`) to readings.
- [x] Add deduplication fields and indexes.
- [x] Implement farm-scoped authorization and role checks.
- [x] Implement `/sync/bootstrap` and `/sync/import` for frontend compatibility.
- [x] Add camelCase serializers matching the existing frontend types.
- [x] Add alert evaluation foundation.
- [x] Add tests for ownership, validation, RBAC, deduplication and history queries.

### Acceptance criteria

- A user can create farms and ponds and only sees their own data.
- Reading history returns correct provenance and timestamps.
- Duplicate client-created records are rejected or returned idempotently.
- Existing `AppData`-shaped data can be imported.
- Alert rules generate alerts without duplicate active alerts.
- Tests cover the full core domain.

---

## 9. Phase 3 — Hardware integration

**Goal:** Secure, reliable device communication through Mosquitto and a firmware foundation that works offline.

### Web backend tasks

- [ ] Finalise Mosquitto configuration: persistence, logging, TLS listener.
- [ ] Add username/password authentication and per-device ACLs.
- [ ] Add Compose service and persistent volume for Mosquitto.
- [ ] Implement device provisioning tokens and claim flow.
- [ ] Store device secrets encrypted with Fernet.
- [ ] Implement MQTT credential/ACL synchronisation command.
- [ ] Implement long-running MQTT worker management command.
- [ ] Ingest telemetry, heartbeat, status and device events.
- [ ] Implement Last Will and Testament handling.
- [ ] Implement command creation, signing, publishing, expiry and acknowledgement.
- [ ] Implement command execution status reporting.
- [ ] Implement configuration publish/acknowledge flow.
- [ ] Add Channels consumers for telemetry, alerts, command status and device status.
- [ ] Add Celery tasks for command expiry, stale-device detection and notification dispatch.
- [ ] Add MQTT authentication, replay-protection and signature tests.
- [ ] Document topic conventions, credentials, ACLs and TLS setup.

### Firmware tasks

- [ ] Create PlatformIO project with Arduino `.ino` entry point.
- [ ] Implement Wi-Fi manager with reconnect and AP fallback.
- [ ] Implement MQTT manager with QoS 1, LWT and TLS support.
- [ ] Implement provisioning and local AP configuration.
- [ ] Implement local web UI or physical interface for readings and manual controls.
- [ ] Implement configurable sensor registry and mock sensors.
- [ ] Implement calibrated analog sensors.
- [ ] Implement actuator manager with safe defaults.
- [ ] Implement local automation rules.
- [ ] Implement independent safety controller.
- [ ] Implement offline LittleFS ring buffer and replay.
- [ ] Implement signed telemetry and command validation.
- [ ] Implement command acknowledgements and execution status.
- [ ] Implement diagnostics and heartbeat.
- [ ] Add host-testable safety and automation tests.
- [ ] Document hardware assumptions and unassigned pin map.

### Acceptance criteria

- A device can claim credentials and connect to Mosquitto.
- Telemetry is persisted once even when replayed.
- Commands are signed, expire, are acknowledged and never bypass safety.
- Device status is retained and disconnected devices are detected.
- Firmware continues local automation when the broker is unavailable.
- MQTT tests pass against a live broker when available; otherwise they are explicitly skipped.
- No hardware success is claimed without physical testing.

---

## 10. Phase 4 — Simulation integration

**Goal:** One telemetry interface for physical and simulated sources.

### Tasks

- [ ] Implement `Simulation` and `SimulationRun` models.
- [ ] Port the planning calculation from `test1.tsx` to a Python service.
- [ ] Preserve the `SimulationRun` input/output contract.
- [ ] Implement `POST /api/v1/simulations`.
- [ ] Add `/api/simulations` compatibility alias.
- [ ] Implement simulation reading and state ingestion.
- [ ] Store simulated readings with `source = simulation`.
- [ ] Add simulation history APIs.
- [ ] Add realtime simulation state over Channels.
- [ ] Add legacy bridge for `techsharks-fishpond-7731/readings` in development.
- [ ] Preserve `fish_pond-live.html` as the canonical demo.
- [ ] Document frontend embedding and telemetry normalisation.

### Acceptance criteria

- A simulation run returns the same shape the frontend already expects.
- Simulated readings are distinguishable from physical readings.
- The existing HTML demo can feed the backend without being rewritten.
- Simulation history is queryable per pond.

---

## 11. Phase 5 — Application ecosystem

**Goal:** Complete the non-core product modules without compromising the core telemetry path.

### Marketplace

- [ ] Categories, listings, inventory and seller profiles.
- [ ] Orders and order status transitions.
- [ ] Seller authorization and ownership checks.
- [ ] Payment provider abstraction with no fake success states.

### Messaging

- [ ] Conversations, participants and messages.
- [ ] Access control and pagination.
- [ ] Realtime message delivery through Channels.

### Help desk

- [ ] Ticket categories, priorities and statuses.
- [ ] Assignment, responses and resolution history.

### Installations and upgrades

- [ ] Installation and upgrade requests.
- [ ] Technician assignment and scheduling.
- [ ] Service history.

### Subscriptions

- [ ] Plans and entitlements.
- [ ] Subscription lifecycle.
- [ ] Renewal information.
- [ ] Disabled-by-default payment provider contract.

### Notifications and administration

- [ ] In-app notifications and preferences.
- [ ] External channel adapters that remain disabled without credentials.
- [ ] Admin user, role and device management.
- [ ] Audit log inspection.

### Acceptance criteria

- Every module enforces permissions and ownership.
- No payment or external notification is marked successful without a real provider.
- Tests cover the main lifecycle of each module.
- Core telemetry functionality is unaffected.

---

## 12. Phase 6 — Frontend integration

**Goal:** Backend-backed operation without breaking the current demo.

### Tasks

- [ ] Add a typed API client under `frontend/fishlink/src/api/`.
- [ ] Add `REACT_APP_API_URL` feature flag.
- [ ] Keep localStorage as fallback when the API is unavailable.
- [ ] Map API responses to existing frontend types.
- [ ] Add local-data import flow.
- [ ] Integrate authentication, farms, ponds, feedings, readings, marketplace and community.
- [ ] Integrate simulation runs and live telemetry.
- [ ] Add offline queueing and retry for frontend mutations.
- [ ] Add tests for API mapping and fallback behaviour.
- [ ] Do not delete `test1.tsx` without explicit approval.

### Acceptance criteria

- The app still works with no backend configured.
- The app works against the backend when configured.
- Existing local data can be imported once without duplicates.
- No UI regression in the current demo path.

---

## 13. Phase 7 — Verification and deployment

**Goal:** A system that can be demonstrated and deployed honestly.

### Tasks

- [ ] Full API integration suite on a disposable PostgreSQL database.
- [ ] Offline and reconnect tests.
- [ ] Duplicate telemetry and command replay tests.
- [ ] Channels WebSocket tests.
- [ ] Firmware host tests for safety and automation logic.
- [ ] Security review: RBAC matrix, CORS, rate limits, JWT, device signatures, secret handling.
- [ ] Load sanity checks for telemetry ingestion.
- [ ] Documentation for local offline operation.
- [ ] Documentation for production deployment, TLS and backups.
- [ ] Documentation for firmware flashing, calibration and hardware assumptions.
- [ ] Final readiness checklist and known-limitations document.

### Acceptance criteria

- All claimed tests pass in a clean environment.
- Skipped tests are explicitly reported as skipped.
- Deployment instructions are reproducible.
- Known limitations are documented without exaggeration.

---

## 14. Cross-cutting workstreams

### Security

- Argon2id passwords.
- JWT rotation and blacklist.
- Permission-based authorization, not frontend-only role checks.
- Device secrets encrypted at rest.
- HMAC signatures, timestamps, expiry and replay protection.
- MQTT ACLs and TLS in production.
- Rate limiting and input validation.
- No secrets in source control.
- Audit logging for sensitive operations.

### Testing strategy

- Unit tests for services, validators, permissions, signatures and calculations.
- API tests for every endpoint group.
- Database tests against PostgreSQL, not SQLite-only assumptions.
- Channels tests with the Channels testing utilities.
- MQTT integration tests only when a broker is available.
- Firmware host tests for pure logic; hardware tests documented as manual.
- No fabricated test results.

### Documentation

- `README.md`: setup and development.
- `docs/architecture.md`: system boundaries and data flow.
- `docs/api.md` / OpenAPI schema.
- `docs/mqtt.md`: topics, payloads, ACLs, TLS.
- `docs/hardware.md`: assumptions, wiring placeholders, calibration.
- `docs/deployment.md`: local offline and production deployment.
- `docs/security.md`: threat model and operational rules.

---

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| No Docker/Redis/Mosquitto on the current machine | Cannot run full stack locally yet | Provide Compose config; use PostgreSQL locally; mark broker-dependent tests skipped until available |
| No hardware or pin map | Firmware cannot be physically validated | Mock sensors, configurable pins, documented assumptions, host tests |
| Public HiveMQ demo topic is insecure | Data exposure and forged commands | Production uses private Mosquitto with ACLs and TLS; legacy bridge is development-only |
| Exposed Velxio credentials in chat export | Unauthorized access | Rotate credentials; never copy them into the repository |
| Two duplicate frontend implementations | Integration ambiguity | Backend supports both contracts; do not delete either without approval |
| Hackathon time pressure | Incomplete ecosystem modules | Prioritise Phases 1–4; keep Phase 5 modular and independently testable |
| Simulated data mistaken for physical data | Misleading analytics | Mandatory `source` provenance and clear frontend labelling |
| Fake payment/notification integrations | Integrity and trust risk | Provider interfaces remain disabled without real credentials |

---

## 16. Definition of done

A phase is complete only when:

- [ ] Implementation is merged into the backend repository.
- [ ] Migrations apply cleanly from zero.
- [ ] Ruff passes.
- [ ] Relevant tests pass, and skipped tests are reported honestly.
- [ ] API documentation is updated.
- [ ] Security and permission implications are reviewed.
- [ ] No secrets or generated credentials are committed.
- [ ] The change can be deployed without modifying the firmware project, or vice versa.

---

## 17. Immediate next actions

1. Scaffold the Django project and `uv` environment.
2. Create the custom user model and initial migrations.
3. Set up PostgreSQL databases and test configuration.
4. Implement authentication, RBAC and API conventions.
5. Add Docker Compose for PostgreSQL, Redis and Mosquitto.
6. Add the first passing test suite and API documentation.
7. Commit Phase 1 as a logical unit.

---

## 18. Change log

| Date | Change |
|---|---|
| 2026-11-11 | Initial roadmap created after repository audit and stack confirmation. |
