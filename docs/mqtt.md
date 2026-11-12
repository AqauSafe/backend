# MQTT and device credentials

AquaSafe uses Eclipse Mosquitto as the MQTT broker. The backend worker subscribes
to device topics; the API publishes signed commands and config messages. Devices
publish telemetry, heartbeats, events, status, command acknowledgements, and config
acknowledgements.

## Topics

Prefix: `aquasafe/v1` (`MQTT_TOPIC_PREFIX`).

| Direction | Topic suffix | Publisher | Subscriber |
|---|---|---|---|
| Device → backend | `/devices/{device_id}/telemetry` | Device | Backend |
| Device → backend | `/devices/{device_id}/heartbeat` | Device | Backend |
| Device → backend | `/devices/{device_id}/events` | Device | Backend |
| Device → backend | `/devices/{device_id}/status` | Device | Backend |
| Backend → device | `/devices/{device_id}/commands` | Backend | Device |
| Device → backend | `/devices/{device_id}/command-acks` | Device | Backend |
| Backend → device | `/devices/{device_id}/config` | Backend | Device |
| Device → backend | `/devices/{device_id}/config-ack` | Device | Backend |

The backend subscribes to QoS 1 filters for every ingress topic. Commands and
config messages are also published at QoS 1. Devices should set a retained Last
Will on their `status` topic with `{"status":"offline"}` and publish
`{"status":"online"}` after connecting.

## Telemetry payload

Telemetry is accepted only on `/devices/{device_id}/telemetry`. At least one
measurement is required; the worker stores a `SensorReading` with
`source = "physical"` and deduplicates by `(deviceId, messageId)`.

| Field | Meaning | Notes |
|---|---|---|
| `temperature` | Water temperature, °C | `temp` alias |
| `oxygen` | Dissolved oxygen, mg/L | `dissolved_oxygen`, `dissolvedOxygen` aliases |
| `ph` | pH | `pH` alias |
| `level` | Water level, percent | `water_level`, `waterLevel` aliases; `0–100` |
| `turbidity_ntu` | Turbidity, NTU | Optional; `turbidityNtu`, `turbidity`, `ntu` aliases; `0–1000` |

Optional fields include `message_id`/`messageId`/`id`, `recorded_at`/
`recordedAt`/`timestamp`/`date`, `raw`, and `metadata`. Invalid numbers are
rejected rather than coerced. The firmware omits `turbidity_ntu` when the sensor
does not provide a turbidity value; older payloads without it remain valid.

```json
{
  "message_id": "msg-123",
  "temperature": 27.5,
  "oxygen": 6.2,
  "ph": 7.4,
  "level": 82.5,
  "turbidity_ntu": 44.25,
  "recorded_at": "2026-11-12T07:20:00Z"
}
```

## Provisioning and credentials

1. An authorized user creates a `Device` and calls
   `POST /api/v1/devices/{id}/provision/` to receive a one-time claim token.
2. The device (or installer) calls `POST /api/v1/devices/claim/` with
   `{"deviceId": "...", "claimToken": "..."}`.
3. The claim response contains **two different secrets**:
   - `mqttPassword`: the broker password. The MQTT username is the `deviceId`.
   - `commandSecret`: the HMAC key used to verify signed commands.
4. Store both secrets in device NVS. Never reuse the broker password as the
   command-signing secret. The claim token is single-use and expires.
5. Regenerate broker credentials and ACLs with:

```bash
uv run python manage.py sync_mqtt_credentials
# or, when mosquitto_passwd is not installed:
uv run python manage.py sync_mqtt_credentials --skip-passwords
```

The command writes per-device ACLs to `mosquitto/config/acl.generated` and updates
`mosquitto/config/passwd` by default. Both files are git-ignored. The repository's
static `mosquitto/config/acl` uses `%u` patterns for local development; production
deployments should point `acl_file` at the generated ACL after review.

Configuration is published by an authorized manager with
`POST /api/v1/devices/{id}/config/` and a JSON body such as
`{"config": {"sampleIntervalSeconds": 30}}`. The backend increments
`configVersion`, publishes the camelCase configuration, and expects a
`config-ack` containing the accepted version.

The firmware applies and persists the configuration. Supported keys are
`sampleIntervalSeconds` (5–3600), `heartbeatIntervalSeconds` (10–3600),
`oxygenTargetMgL` (0–20), and `safety` limits: `oxygenMinMgL`,
`oxygenCriticalMgL`, `oxygenHysteresisMgL`, `temperatureMaxC`, `phMin`, `phMax`,
and `waterLevelMinPercent`. Invalid values are rejected with
`{"accepted": false, "error": "..."}` and are not applied.

Provisioned devices must publish signed telemetry envelopes. The signature covers
the exact telemetry JSON body, not a reconstructed object:

```json
{"payload":"{\"message_id\":\"...\",...}","signature":"hex-hmac-sha256"}
```

The HMAC key is the device `commandSecret`. Unsigned telemetry is rejected for a
device that has a command secret. Devices without a provisioned secret remain
usable only for legacy development ingestion.

Command signatures use HMAC-SHA256 over:

```text
{command_id}\n{device_id}\n{type}\n{expires_at}\n{canonical-payload-json}
```

`canonical-payload-json` is sorted-key, compact JSON. Commands expire after their
`expires_at` timestamp and are acknowledged through `command-acks`. Local firmware
safety always overrides remote actuator commands.

## Running the worker

```bash
uv run python manage.py run_mqtt_worker
```

The worker verifies MQTT authentication through the broker, validates topic
ownership, deduplicates telemetry by `message_id`, persists readings/heartbeats/
events, evaluates alerts, updates command acknowledgements, and broadcasts farm
updates over Channels.

## TLS

For production, uncomment the `8883` listener in `mosquitto/config/mosquitto.conf`
and mount CA, server certificate, and key files under
`mosquitto/config/certs/`. Set on the backend and worker:

```dotenv
MQTT_PORT=8883
MQTT_TLS=true
MQTT_CA_CERTS=/path/to/ca.crt
```

Use `mqtts://`-equivalent TLS settings in the firmware (define
`AQUASAFE_MQTT_TLS` and `AQUASAFE_MQTT_CA_CERT`). Do not enable plaintext MQTT on a
public network. The local development broker is plaintext on port 1883.

## Verification limits

The backend tests monkeypatch publishing and do not require a live broker. Live
Mosquitto, TLS, credential sync, retained LWT, and reconnect behavior must be
verified in an environment where Mosquitto/Redis are installed. Do not report those
paths as validated until that integration test is run.
