#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>

namespace aquasafe {

struct SensorReading {
    bool valid = false;
    float temperature_c = 0.0f;
    float oxygen_mg_l = 0.0f;
    float ph = 7.0f;
    float water_level_pct = 0.0f;
    std::uint32_t recorded_at = 0;
    bool has_turbidity = false;
    float turbidity_ntu = 0.0f;
};

struct SafetyLimits {
    float oxygen_min = 5.0f;
    float oxygen_critical = 3.0f;
    float oxygen_hysteresis = 0.5f;
    float temperature_max = 32.0f;
    float ph_min = 6.5f;
    float ph_max = 9.0f;
    float water_level_min = 20.0f;
};

struct SafetyDecision {
    bool force_aerator = false;
    bool emergency_stop = false;
    const char* reason = "normal";
};

class SafetyController {
public:
    explicit SafetyController(SafetyLimits limits = {}) : limits_(limits) {}

    SafetyDecision evaluate(const SensorReading& reading);
    void reset();
    bool emergency_latched() const { return emergency_latched_; }
    const SafetyLimits& limits() const { return limits_; }
    void set_limits(const SafetyLimits& limits) { limits_ = limits; }

private:
    SafetyLimits limits_;
    bool emergency_latched_ = false;
    bool aeration_latched_ = false;
};

struct AutomationDecision {
    bool aerator_on = false;
    const char* reason = "idle";
};

class AutomationEngine {
public:
    explicit AutomationEngine(float oxygen_target = 5.5f) : oxygen_target_(oxygen_target) {}

    AutomationDecision evaluate(const SensorReading& reading, const SafetyDecision& safety) const;
    void set_oxygen_target(float target) { oxygen_target_ = target; }

private:
    float oxygen_target_;
};

struct ActuatorState {
    bool aerator_on = false;
    bool remote_requested = false;
    bool safety_override = false;
    const char* reason = "idle";
};

class ActuatorManager {
public:
    void set_remote_aerator(bool on);
    void apply(const SafetyDecision& safety, const AutomationDecision& automation);
    ActuatorState state() const { return state_; }
    void reset();

private:
    ActuatorState state_;
};

struct TelemetryRecord {
    std::uint32_t recorded_at = 0;
    float temperature_c = 0.0f;
    float oxygen_mg_l = 0.0f;
    float ph = 7.0f;
    float water_level_pct = 0.0f;
    bool has_turbidity = false;
    float turbidity_ntu = 0.0f;
};

template <std::size_t Capacity>
class RingBuffer {
public:
    bool push(const TelemetryRecord& record) {
        records_[head_] = record;
        head_ = (head_ + 1) % Capacity;
        if (size_ < Capacity) {
            ++size_;
            return false;
        }
        return true;
    }

    bool empty() const { return size_ == 0; }
    bool full() const { return size_ == Capacity; }
    std::size_t size() const { return size_; }
    std::size_t capacity() const { return Capacity; }

    const TelemetryRecord& at(std::size_t index) const {
        const std::size_t oldest = (head_ + Capacity - size_) % Capacity;
        return records_[(oldest + index) % Capacity];
    }

    void clear() {
        head_ = 0;
        size_ = 0;
    }

private:
    std::array<TelemetryRecord, Capacity> records_{};
    std::size_t head_ = 0;
    std::size_t size_ = 0;
};

std::string hmac_sha256_hex(std::string_view key, std::string_view message);
bool verify_hmac_sha256(std::string_view key, std::string_view message, std::string_view signature_hex);
std::string sha256_hex(std::string_view message);

struct CommandEnvelope {
    std::string command_id;
    std::string command_type;
    std::string payload;
    std::string expires_at;
    std::string signature;
};

bool command_is_expired(const CommandEnvelope& command, std::string_view now_iso8601);
bool verify_command(const CommandEnvelope& command, std::string_view device_id, std::string_view secret);

std::string telemetry_json(std::string_view device_id, std::string_view message_id,
                           const TelemetryRecord& record);
std::string telemetry_envelope_json(std::string_view device_id, std::string_view message_id,
                                    const TelemetryRecord& record, std::string_view secret);

}  // namespace aquasafe
