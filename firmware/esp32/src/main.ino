#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

#include "DeviceConfig.h"
#include "MqttManager.h"
#include "OfflineQueue.h"
#include "ProvisioningPortal.h"
#include "SensorRegistry.h"
#include "WifiManager.h"
#include "aquasafe_core.h"

DeviceConfig config;
WifiManager wifi;
ProvisioningPortal portal;
MqttManager mqtt;
SensorRegistry sensors;
OfflineQueue offline;
aquasafe::SafetyController safety;
aquasafe::AutomationEngine automation(5.5f);
aquasafe::ActuatorManager actuators;

aquasafe::SensorReading latest_reading;
uint32_t last_read_ms = 0;
uint32_t last_control_ms = 0;
uint32_t last_heartbeat_ms = 0;
uint32_t last_replay_ms = 0;
uint32_t read_interval_ms = AQUASAFE_READ_INTERVAL_MS;
uint32_t heartbeat_interval_ms = AQUASAFE_HEARTBEAT_INTERVAL_MS;
uint32_t config_version = 0;
constexpr size_t kRecentCommandLimit = 8;
String recent_command_ids[kRecentCommandLimit];
size_t recent_command_index = 0;
bool telemetry_secret_warned = false;

bool rememberCommand(const String& command_id) {
    for (const auto& recent : recent_command_ids) {
        if (recent == command_id) {
            return false;
        }
    }
    recent_command_ids[recent_command_index] = command_id;
    recent_command_index = (recent_command_index + 1) % kRecentCommandLimit;
    return true;
}

String isoNow() {
    const time_t now = time(nullptr);
    struct tm utc {};
    gmtime_r(&now, &utc);
    char buffer[32];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S+00:00", &utc);
    return String(buffer);
}

String newMessageId() {
    char buffer[48];
    snprintf(buffer, sizeof(buffer), "%08lx-%08lx-%lu",
             static_cast<unsigned long>(ESP.getEfuseMac() >> 32),
             static_cast<unsigned long>(ESP.getEfuseMac() & 0xffffffffUL),
             static_cast<unsigned long>(millis()));
    return String(buffer);
}

void publishAck(const String& command_id, bool success, const String& error = "") {
    JsonDocument doc;
    doc["command_id"] = command_id;
    doc["success"] = success;
    if (!error.isEmpty()) {
        doc["error"] = error;
    }
    String body;
    serializeJson(doc, body);
    mqtt.publish(mqtt.topic("command-acks"), body);
}

void publishEvent(const String& type, const String& severity, const String& message) {
    JsonDocument doc;
    doc["event_type"] = type;
    doc["severity"] = severity;
    doc["message"] = message;
    doc["recorded_at"] = isoNow();
    String body;
    serializeJson(doc, body);
    mqtt.publish(mqtt.topic("events"), body);
}

void applyControl() {
    latest_reading = sensors.read();
    const time_t now = time(nullptr);
    latest_reading.recorded_at = now > 1700000000 ? static_cast<uint32_t>(now) : 0;
    const auto safety_decision = safety.evaluate(latest_reading);
    const auto automation_decision = automation.evaluate(latest_reading, safety_decision);
    actuators.apply(safety_decision, automation_decision);
}

String currentTelemetryEnvelope() {
    const auto& settings = config.settings();
    if (settings.device_secret.isEmpty()) {
        if (!telemetry_secret_warned) {
            telemetry_secret_warned = true;
            publishEvent("telemetry.signing_unavailable", "warning",
                         "Command secret is not provisioned; telemetry is not sent.");
        }
        return "";
    }
    aquasafe::TelemetryRecord record;
    record.recorded_at = latest_reading.recorded_at;
    record.temperature_c = latest_reading.temperature_c;
    record.oxygen_mg_l = latest_reading.oxygen_mg_l;
    record.ph = latest_reading.ph;
    record.water_level_pct = latest_reading.water_level_pct;
    record.has_turbidity = latest_reading.has_turbidity;
    record.turbidity_ntu = latest_reading.turbidity_ntu;
    return aquasafe::telemetry_envelope_json(settings.device_id.c_str(),
                                             newMessageId().c_str(), record,
                                             settings.device_secret.c_str())
        .c_str();
}

void publishTelemetry() {
    const String body = currentTelemetryEnvelope();
    if (body.isEmpty()) {
        return;
    }
    if (!mqtt.connected() || !mqtt.publish(mqtt.topic("telemetry"), body)) {
        offline.enqueue(body);
    }
}

void publishHeartbeat() {
    JsonDocument doc;
    doc["status"] = "online";
    doc["rssi"] = WiFi.RSSI();
    doc["uptime_seconds"] = millis() / 1000UL;
    doc["recorded_at"] = isoNow();
    String body;
    serializeJson(doc, body);
    mqtt.publish(mqtt.topic("heartbeat"), body);
}

bool applyConfig(JsonDocument& doc, String& error) {
    JsonObjectConst config = doc["config"].as<JsonObjectConst>();
    if (config.isNull()) {
        error = "missing config object";
        return false;
    }
    if (config["sampleIntervalSeconds"].is<uint32_t>()) {
        const uint32_t seconds = config["sampleIntervalSeconds"].as<uint32_t>();
        if (seconds < 5 || seconds > 3600) {
            error = "sampleIntervalSeconds out of range";
            return false;
        }
        read_interval_ms = seconds * 1000UL;
    }
    if (config["heartbeatIntervalSeconds"].is<uint32_t>()) {
        const uint32_t seconds = config["heartbeatIntervalSeconds"].as<uint32_t>();
        if (seconds < 10 || seconds > 3600) {
            error = "heartbeatIntervalSeconds out of range";
            return false;
        }
        heartbeat_interval_ms = seconds * 1000UL;
    }
    if (config["oxygenTargetMgL"].is<float>()) {
        const float target = config["oxygenTargetMgL"].as<float>();
        if (target < 0.0f || target > 20.0f) {
            error = "oxygenTargetMgL out of range";
            return false;
        }
        automation.set_oxygen_target(target);
    }

    aquasafe::SafetyLimits limits = safety.limits();
    JsonObjectConst safety_config = config["safety"].as<JsonObjectConst>();
    if (!safety_config.isNull()) {
        if (safety_config["oxygenMinMgL"].is<float>())
            limits.oxygen_min = safety_config["oxygenMinMgL"].as<float>();
        if (safety_config["oxygenCriticalMgL"].is<float>())
            limits.oxygen_critical = safety_config["oxygenCriticalMgL"].as<float>();
        if (safety_config["oxygenHysteresisMgL"].is<float>())
            limits.oxygen_hysteresis = safety_config["oxygenHysteresisMgL"].as<float>();
        if (safety_config["temperatureMaxC"].is<float>())
            limits.temperature_max = safety_config["temperatureMaxC"].as<float>();
        if (safety_config["phMin"].is<float>())
            limits.ph_min = safety_config["phMin"].as<float>();
        if (safety_config["phMax"].is<float>())
            limits.ph_max = safety_config["phMax"].as<float>();
        if (safety_config["waterLevelMinPercent"].is<float>())
            limits.water_level_min = safety_config["waterLevelMinPercent"].as<float>();
    }
    if (limits.oxygen_min < 0.0f || limits.oxygen_critical < 0.0f ||
        limits.oxygen_critical > limits.oxygen_min || limits.temperature_max <= 0.0f ||
        limits.ph_min < 0.0f || limits.ph_max > 14.0f || limits.ph_min >= limits.ph_max ||
        limits.water_level_min < 0.0f || limits.water_level_min > 100.0f) {
        error = "invalid safety limits";
        return false;
    }
    safety.set_limits(limits);
    return true;
}

void handleConfig(const String& body) {
    JsonDocument doc;
    String error;
    bool accepted = !deserializeJson(doc, body);
    if (!accepted) {
        error = "invalid config JSON";
    } else {
        accepted = applyConfig(doc, error);
    }
    const uint32_t version = doc["version"] | config_version;
    if (accepted) {
        config_version = version;
        String stored;
        serializeJson(doc, stored);
        config.saveRemoteConfig(stored, version);
    }
    JsonDocument ack;
    ack["version"] = version;
    ack["accepted"] = accepted;
    if (!accepted) {
        ack["error"] = error;
        publishEvent("config.rejected", "warning", error);
    }
    String response;
    serializeJson(ack, response);
    mqtt.publish(mqtt.topic("config-ack"), response);
}

void handleCommand(const String& topic, const String& body) {
    if (topic.endsWith("/config")) {
        handleConfig(body);
        return;
    }
    if (!topic.endsWith("/commands")) {
        return;
    }
    JsonDocument doc;
    const auto error = deserializeJson(doc, body);
    if (error) {
        Serial.printf("Invalid command JSON: %s\n", error.c_str());
        return;
    }

    aquasafe::CommandEnvelope command;
    command.command_id = doc["command_id"].as<String>().c_str();
    command.command_type = doc["type"].as<String>().c_str();
    command.expires_at = doc["expires_at"].as<String>().c_str();
    command.signature = doc["signature"].as<String>().c_str();
    String payload_json;
    serializeJson(doc["payload"], payload_json);
    command.payload = payload_json.c_str();

    const auto& settings = config.settings();
    if (settings.device_secret.isEmpty()) {
        publishAck(command.command_id.c_str(), false, "device secret is not configured");
        return;
    }
    if (!aquasafe::verify_command(command, settings.device_id.c_str(),
                                  settings.device_secret.c_str())) {
        publishAck(command.command_id.c_str(), false, "invalid command signature");
        return;
    }
    if (time(nullptr) < 1700000000) {
        publishAck(command.command_id.c_str(), false, "clock is not synchronized");
        return;
    }
    if (aquasafe::command_is_expired(command, isoNow().c_str())) {
        publishAck(command.command_id.c_str(), false, "command has expired");
        return;
    }
    const String command_id = command.command_id.c_str();
    if (!rememberCommand(command_id)) {
        publishAck(command_id, true);
        return;
    }

    if (command.command_type == "aerator.set") {
        actuators.set_remote_aerator(doc["payload"]["on"] | false);
        publishAck(command.command_id.c_str(), true);
    } else if (command.command_type == "safety.reset") {
        safety.reset();
        publishAck(command.command_id.c_str(), true);
    } else if (command.command_type == "device.reboot") {
        publishAck(command.command_id.c_str(), true);
        delay(200);
        ESP.restart();
    } else {
        publishAck(command.command_id.c_str(), false, "unsupported command type");
    }
}

String localStatusJson() {
    applyControl();
    JsonDocument doc;
    doc["device_id"] = config.settings().device_id;
    doc["config_version"] = config_version;
    doc["reading"]["valid"] = latest_reading.valid;
    doc["reading"]["temperature_c"] = latest_reading.temperature_c;
    doc["reading"]["oxygen_mg_l"] = latest_reading.oxygen_mg_l;
    doc["reading"]["ph"] = latest_reading.ph;
    doc["reading"]["water_level_pct"] = latest_reading.water_level_pct;
    if (latest_reading.has_turbidity) {
        doc["reading"]["turbidity_ntu"] = latest_reading.turbidity_ntu;
    }
    const auto state = actuators.state();
    doc["actuator"]["aerator_on"] = state.aerator_on;
    doc["actuator"]["remote_requested"] = state.remote_requested;
    doc["actuator"]["safety_override"] = state.safety_override;
    doc["actuator"]["reason"] = state.reason;
    doc["safety"]["emergency_latched"] = safety.emergency_latched();
    String body;
    serializeJson(doc, body);
    return body;
}

void setup() {
    Serial.begin(115200);
    config.begin();
    if (config.settings().remote_config.length() > 0) {
        JsonDocument stored;
        if (!deserializeJson(stored, config.settings().remote_config)) {
            String error;
            if (applyConfig(stored, error)) {
                config_version = config.settings().remote_config_version;
            } else {
                Serial.printf("Stored config was not applied: %s\n", error.c_str());
            }
        }
    }
    portal.onStatus([]() { return localStatusJson(); });
    portal.onControl([](const String& action, bool value, String& error) {
        if (action == "aerator") {
            actuators.set_remote_aerator(value);
            applyControl();
            return true;
        }
        if (action == "safety.reset") {
            safety.reset();
            actuators.reset();
            applyControl();
            return true;
        }
        error = "unsupported action";
        return false;
    });
    wifi.begin(config);

    if (wifi.fallbackAp()) {
        Serial.printf("Provisioning portal at http://%s/\n", wifi.localIp().toString().c_str());
        portal.begin(config);
        return;
    }

    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    offline.begin();
    mqtt.begin(config);
    mqtt.onMessage(handleCommand);
    mqtt.loop();

    applyControl();
    publishEvent("device.booted", "info", "AquaSafe firmware " AQUASAFE_FIRMWARE_VERSION " booted");
}

void loop() {
    if (wifi.fallbackAp()) {
        portal.loop();
        return;
    }

    wifi.loop();
    mqtt.loop();

    const uint32_t now = millis();
    if (now - last_control_ms >= 2000UL || last_control_ms == 0) {
        last_control_ms = now;
        applyControl();
    }
    if (now - last_read_ms >= read_interval_ms || last_read_ms == 0) {
        last_read_ms = now;
        if (mqtt.connected()) {
            publishTelemetry();
        } else {
            const String body = currentTelemetryEnvelope();
            if (!body.isEmpty()) {
                offline.enqueue(body);
            }
        }
    }
    if (mqtt.connected() && (now - last_heartbeat_ms >= heartbeat_interval_ms ||
                             last_heartbeat_ms == 0)) {
        last_heartbeat_ms = now;
        publishHeartbeat();
    }
    if (mqtt.connected() && (now - last_replay_ms >= 30000UL || last_replay_ms == 0)) {
        last_replay_ms = now;
        offline.replay([](const String& line) {
            return mqtt.publish(mqtt.topic("telemetry"), line);
        });
    }
    delay(10);
}
