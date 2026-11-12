# Simulation integration

AquaSafe stores deterministic planning runs separately from live simulated sensor
state. Both are available through the versioned API.

## Planning run contract

`POST /api/v1/simulations/` and the compatibility alias `POST /api/simulations`
accept the fields already used by `frontend/fishlink/src/test1.tsx`:

```json
{
  "pondId": "uuid",
  "durationDays": 90,
  "startingWeightG": 20,
  "dailyGrowthG": 2.5,
  "dailyFeedKg": 3,
  "dailyMortalityPercent": 1,
  "temperatureC": 28,
  "dissolvedOxygenMgL": 6,
  "ph": 7.2
}
```

The response adds the run ID and timestamp while preserving the existing field
names and numeric types:

```json
{
  "id": "uuid",
  "farmId": "uuid",
  "pondId": "uuid",
  "createdAt": "2026-11-11T10:00:00Z",
  "formulaVersion": "aquasafe-simple-v1",
  "population": 1000,
  "durationDays": 90,
  "startingWeightG": 20.0,
  "dailyGrowthG": 2.5,
  "dailyFeedKg": 3.0,
  "dailyMortalityPercent": 1.0,
  "temperatureC": 28.0,
  "dissolvedOxygenMgL": 6.0,
  "ph": 7.2,
  "projectedSurvivors": 405,
  "projectedBiomassKg": 99.23,
  "totalFeedKg": 270.0,
  "estimatedFcr": 3.41,
  "warnings": [],
  "dailyProjection": [{"day": 1, "survivors": 990, "averageWeightG": 22.5,
    "biomassKg": 22.28, "cumulativeFeedKg": 3.0}, "..."]
}
```

`GET /api/v1/simulations/` is paginated and filterable with `pondId` or `farmId`.
`GET /api/v1/simulations/{id}/` returns one run. Runs are immutable.

The Python service mirrors `test1.tsx`: temperature stress outside 26–30°C, oxygen
stress below 5 mg/L, pH stress outside 6.5–8.5, a daily loss cap of 5%, survivors
after compounding loss, projected biomass from surviving fish, total feed, and FCR
from positive biomass gain. Warning strings intentionally match the frontend.

## Live simulation state

`POST /api/v1/simulations/state/` accepts any subset of `temperature`, `oxygen`,
`ph`, `level`, and `turbidityNtu`, plus optional `pondId`, `recordedAt`,
`clientId`, and `messageId`. It:

1. Creates or updates the pond's `Simulation` state.
2. Stores a `SensorReading` with `source = "simulation"`.
3. Evaluates alert rules and broadcasts `simulation.state` to the farm WebSocket.
4. Returns the simulation and reading.

At least one measurement is required. `level` is a percentage from `0` to `100`.
`turbidityNtu` is optional and uses NTU from `0` to `1000`; the backend field is
`turbidity_ntu`. Requests and responses use the normal camelCase API boundary
(`pondId`, `turbidityNtu`, `lastStateAt`).

`GET /api/v1/simulations/state/?pondId=...` returns the latest state:

```json
{
  "data": {
    "id": "uuid",
    "farmId": "uuid",
    "pondId": "uuid",
    "isActive": true,
    "state": {
      "temperature": 27.5,
      "oxygen": 6.2,
      "ph": 7.4,
      "level": 82.5,
      "turbidityNtu": 44.25,
      "recordedAt": "2026-11-12T07:20:00Z"
    },
    "lastStateAt": "2026-11-12T07:20:00Z"
  }
}
```

Omit `pondId` to list accessible simulation states.

## Realtime degradation

Live state is persisted first, so `GET /api/v1/simulations/state/` and
`GET /api/v1/readings/latest/` remain the source of truth even when Channels is
unavailable. `broadcast_farm_event` is best-effort: if Redis or the channel layer
cannot deliver a message, the mutation still succeeds and a warning is logged. The
React live-pond view therefore polls the REST endpoints every five seconds rather
than requiring a WebSocket connection.

## Legacy fish_pond-live bridge

The original HTML demo publishes raw 0..1023 ADC values (`t`, `p`, `o`, `l`) to
`techsharks-fishpond-7731/readings`. The development-only bridge normalises:

- oxygen: `o / 1023 * 12` mg/L
- pH: `p / 1023 * 14`
- water level: `l / 1023 * 100` percent
- turbidity: `t / 1023 * 100` NTU, stored in `turbidity_ntu` and `raw.turbidityNtu`

Named values (`do`, `ph`, `lvl`, `ntu`, `temperature`) take precedence when
present. Enable the bridge only for local development:

```dotenv
DEBUG=true
SIMULATION_LEGACY_BRIDGE_ENABLED=true
SIMULATION_LEGACY_BRIDGE_POND_ID=<pond uuid>
SIMULATION_LEGACY_MQTT_HOST=broker.hivemq.com
SIMULATION_LEGACY_MQTT_PORT=1883
SIMULATION_LEGACY_TOPIC=techsharks-fishpond-7731/readings
```

```bash
uv run python manage.py run_simulation_bridge
```

The bridge inserts and updates `Simulation` state and does not rewrite
`fish_pond-live.html`. The HTML file remains the canonical demo. The public broker
is not production infrastructure and must not receive AquaSafe credentials.

## Embedded frontend visualization

The React app embeds the editable copy at
`frontend/fishlink/public/fish_pond-live.html`; the canonical
`frontend/fish_pond-live.html` is not modified. The iframe is loaded with:

```text
/fish_pond-live.html?embedded=1&pondId=<uuid>
```

The embedded page does not load `mqtt.js` or connect to the public HiveMQ broker.
Instead it posts `{"type":"fishlink:ready","pondId":"<uuid>"}` to the parent, and
the React page sends:

```json
{"type":"fishlink:status","status":"live|waiting|stale|offline|error|idle","lastFetchedAt":0}
{"type":"fishlink:reading","reading":{"pondId":"uuid","temperature":27.5,"oxygen":6.2,"ph":7.4,"level":82.5,"turbidityNtu":44.25,"recordedAt":"2026-11-12T07:20:00Z","source":"manual"}}
```

The bridge maps values into the animation without changing the simulation
formula: water level is divided by `100`, turbidity by `100`, pH by `14`, oxygen by
`12`, and temperature is used directly, then clamped to the animation's supported
range. Readings older than 15 seconds are shown as stale and older than 60 seconds
as sensor offline; the animation keeps the last values visible but never labels
them live. Standalone use of the HTML file still loads `mqtt.js` dynamically and
retains the original broker path.
