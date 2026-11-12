#include "aquasafe_core.h"

#include <cassert>
#include <cstring>
#include <iostream>

using namespace aquasafe;

namespace {

void test_safety_and_recovery() {
    SafetyLimits limits;
    SafetyController safety(limits);
    SensorReading reading{true, 27.0f, 4.0f, 7.2f, 80.0f, 0};
    auto decision = safety.evaluate(reading);
    assert(decision.force_aerator);
    assert(!decision.emergency_stop);

    reading.oxygen_mg_l = 5.2f;
    decision = safety.evaluate(reading);
    assert(decision.force_aerator);
    assert(std::strcmp(decision.reason, "water quality outside safe range") == 0);

    reading.oxygen_mg_l = 5.6f;
    decision = safety.evaluate(reading);
    assert(!decision.force_aerator);
}

void test_emergency_latch_requires_reset() {
    SafetyController safety;
    SensorReading reading{true, 27.0f, 2.5f, 7.2f, 80.0f, 0};
    assert(safety.evaluate(reading).emergency_stop);
    reading.oxygen_mg_l = 8.0f;
    assert(safety.evaluate(reading).emergency_stop);
    safety.reset();
    assert(!safety.evaluate(reading).emergency_stop);
}

void test_automation_and_actuator_override() {
    AutomationEngine automation(5.5f);
    SensorReading reading{true, 27.0f, 5.0f, 7.2f, 80.0f, 0};
    SafetyDecision safety{true, false, "low oxygen"};
    auto decision = automation.evaluate(reading, safety);
    assert(decision.aerator_on);

    ActuatorManager actuator;
    actuator.set_remote_aerator(false);
    actuator.apply(safety, decision);
    assert(actuator.state().aerator_on);
    assert(actuator.state().safety_override);

    SafetyDecision normal;
    decision = automation.evaluate(reading, normal);
    assert(decision.aerator_on);
    actuator.apply(normal, decision);
    assert(actuator.state().aerator_on);
}

void test_ring_buffer_wraps() {
    RingBuffer<3> buffer;
    buffer.push({1, 20.0f, 6.0f, 7.0f, 80.0f});
    buffer.push({2, 21.0f, 6.1f, 7.1f, 81.0f});
    buffer.push({3, 22.0f, 6.2f, 7.2f, 82.0f});
    assert(buffer.full());
    assert(buffer.at(0).recorded_at == 1);
    buffer.push({4, 23.0f, 6.3f, 7.3f, 83.0f});
    assert(buffer.at(0).recorded_at == 2);
    assert(buffer.at(2).recorded_at == 4);
    assert(buffer.size() == 3);
}

void test_hashes() {
    assert(sha256_hex("abc") ==
           "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    assert(hmac_sha256_hex("Jefe", "what do ya want for nothing?") ==
           "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843");
}

void test_command_signature() {
    CommandEnvelope command;
    command.command_id = "3f80d33a-2732-4b55-b75d-1b9f5d8f1f7e";
    command.command_type = "aerator.set";
    command.expires_at = "2026-11-11T10:01:00+00:00";
    command.payload = "{\"on\":true}";
    const std::string canonical = command.command_id + "\n" + "esp32-1\n" + command.command_type +
                                  "\n" + command.expires_at + "\n" + command.payload;
    command.signature = hmac_sha256_hex("device-secret", canonical);

    assert(verify_command(command, "esp32-1", "device-secret"));
    assert(!verify_command(command, "esp32-2", "device-secret"));
    assert(!command_is_expired(command, "2026-11-11T10:00:00+00:00"));
    assert(command_is_expired(command, "2026-11-11T10:02:00+00:00"));
}

void test_telemetry_json() {
    TelemetryRecord record{1762816800, 27.5f, 6.2f, 7.1f, 80.0f};
    const auto json = telemetry_json("esp32-1", "message-1", record);
    assert(json.find("\"message_id\":\"message-1\"") != std::string::npos);
    assert(json.find("\"oxygen\":6.20") != std::string::npos);
    assert(json.find("\"recorded_at\":1762816800") != std::string::npos);
    assert(json.find("turbidityNtu") == std::string::npos);

    TelemetryRecord turbid_record{1762816800, 27.5f, 6.2f, 7.1f, 80.0f, true, 18.5f};
    const auto turbid_json = telemetry_json("esp32-1", "message-1", turbid_record);
    assert(turbid_json.find("\"turbidityNtu\":18.50") != std::string::npos);

    const auto envelope = telemetry_envelope_json("esp32-1", "message-1", record, "device-secret");
    assert(envelope.find("\"payload\":\"{\\\"message_id\\\"") != std::string::npos);
    assert(envelope.find("\"signature\":\"") != std::string::npos);
    assert(envelope.find(hmac_sha256_hex("device-secret", json)) != std::string::npos);
    assert(envelope.size() > json.size() + 64);
}

}  // namespace

int main() {
    test_safety_and_recovery();
    test_emergency_latch_requires_reset();
    test_automation_and_actuator_override();
    test_ring_buffer_wraps();
    test_hashes();
    test_command_signature();
    test_telemetry_json();
    std::cout << "aquasafe core firmware tests passed\n";
    return 0;
}
