# AquaSafe ESP32 firmware

Offline-first aquaculture controller for the AquaSafe backend. The firmware keeps
local safety and automation active when Wi-Fi or MQTT is unavailable.

## Status

This is a foundation, not a validated production controller. It has been compiled
only as host-side C++ tests. It has **not** been built with PlatformIO, flashed to
an ESP32, or tested against pumps, relays, dissolved-oxygen probes, or real ponds.

No GPIO pin map is defined because none has been confirmed for the target board.
`SensorRegistry` therefore returns clearly marked mock readings. Replace it with a
real sensor driver after confirming board wiring, electrical isolation, probe
calibration, and fail-safe relay behavior.

## Layout

- `lib/aquasafe_core`: portable safety, automation, actuator, ring-buffer, HMAC,
  command-verification, and telemetry-serialization logic.
- `src`: Arduino entry point and Wi-Fi, MQTT, provisioning, sensor, and offline
  queue adapters.
- `test/test_core.cpp`: host tests for safety recovery, emergency latching,
  actuator override, ring-buffer behavior, HMAC/SHA-256, command signatures,
  telemetry JSON and signed telemetry envelopes.

## Build and host tests

```bash
cd backend/firmware/esp32
./test/run_host_tests.sh
```

Target build (requires PlatformIO):

```bash
pio run
pio run --target upload
pio device monitor
```

Copy `include/secrets.example.h` to `include/secrets.h` only for local development.
`secrets.h` is git-ignored. For field devices, use the local provisioning portal
instead of compiling credentials into an image.

## Provisioning

If Wi-Fi is missing or unavailable, the device starts an access point named
`AquaSafe-<chip-id>` and a configuration portal at `http://192.168.4.1/`. The
default access-point password is `aquasafe-setup`; change `AQUASAFE_AP_PASSWORD` in
`include/config.h` before deployment. The portal stores Wi-Fi, MQTT, device ID, and
device secret in NVS and restarts the board.

Provision the device secret only after claiming it through the AquaSafe API. Do not
reuse the broker password as the command-signing secret.

When running in AP fallback, the portal also shows the latest mock reading, actuator
and safety state, and provides local aerator on/off and safety-reset controls. The
firmware never exposes those controls on the station network; use MQTT commands and
the backend UI in normal operation.

Remote configuration is persisted in NVS and reapplied after reboot. Supported keys
are `sampleIntervalSeconds`, `heartbeatIntervalSeconds`, `oxygenTargetMgL`, and a
`safety` object containing `oxygenMinMgL`, `oxygenCriticalMgL`,
`oxygenHysteresisMgL`, `temperatureMaxC`, `phMin`, `phMax`, and
`waterLevelMinPercent`. Invalid configuration is rejected without changing the
active limits.

## MQTT contract

Topic prefix: `aquasafe/v1`

- Publish telemetry: `.../devices/{device_id}/telemetry`
- Publish heartbeat: `.../devices/{device_id}/heartbeat`
- Publish events: `.../devices/{device_id}/events`
- Publish online/offline LWT: `.../devices/{device_id}/status`
- Subscribe commands: `.../devices/{device_id}/commands`
- Publish command acknowledgements: `.../devices/{device_id}/command-acks`
- Subscribe configuration: `.../devices/{device_id}/config`
- Publish configuration acknowledgements: `.../devices/{device_id}/config-ack`

Telemetry envelope:

```json
{"payload":"{\"message_id\":\"...\",\"device_id\":\"esp32-1\",\"recorded_at\":1762816800,\"temperature\":27.5,\"oxygen\":6.2,\"ph\":7.1,\"level\":80.0}","signature":"hex-hmac-sha256"}
```

The signature is HMAC-SHA256 over the exact payload string using the device command
secret. Unsigned telemetry is not sent when no secret is provisioned; the firmware
publishes a `telemetry.signing_unavailable` event instead. `recorded_at` is Unix UTC
seconds when the clock is synchronized; `0` means the backend should use receipt
time. The backend deduplicates by `message_id`.

Command envelope:

```json
{"command_id":"...","device_id":"esp32-1","type":"aerator.set",
 "payload":{"on":true},"expires_at":"2026-11-11T10:01:00+00:00",
 "signature":"hex-hmac-sha256"}
```

The HMAC-SHA256 signature covers this exact UTF-8 string:

```text
{command_id}\n{device_id}\n{type}\n{expires_at}\n{payload-json}
```

`payload-json` must be canonical JSON with sorted keys and compact separators. The
backend produces that form. The firmware serializes the received payload object;
ArduinoJson preserves the parsed member order, but this must be verified against
the backend before production use. Commands are rejected if the signature is
invalid, the device secret is missing, the clock is unsynchronized, or the command
has expired.

Supported commands: `aerator.set`, `safety.reset`, `device.reboot`. Local safety
always overrides remote aerator requests. A critical safety condition latches until
an authenticated `safety.reset`, and the actuator manager is currently state-only
until a certified relay/output stage is defined. Recent command IDs are kept in a
small RAM cache to ignore MQTT QoS 1 duplicates; the cache does not survive reboot.

## Security notes

- MQTT is plaintext by default. Define `AQUASAFE_MQTT_TLS` and provide
  `AQUASAFE_MQTT_CA_CERT` before using MQTT over TLS.
- The provisioning portal is HTTP on a local WPA2 access point. Use a unique AP
  password and provision devices on a trusted bench, not an untrusted network.
- Secrets are stored in ESP32 NVS, which is not encrypted by default. Enable flash
  encryption and secure boot for production hardware.
- Do not connect pumps or mains-powered equipment without a qualified electrical
  design, independent fail-safe circuitry, and local emergency stop.
