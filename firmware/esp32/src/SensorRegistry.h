#pragma once

#include <Arduino.h>

#include "aquasafe_core.h"

class SensorRegistry {
public:
    aquasafe::SensorReading read() {
        // No physical pin map or sensor models are confirmed. Mock values are
        // deliberately varied so safety and offline automation can be tested.
        const uint32_t tick = millis() / 1000UL;
        aquasafe::SensorReading reading;
        reading.valid = true;
        reading.temperature_c = 27.0f + static_cast<float>(tick % 10) * 0.15f;
        reading.oxygen_mg_l = 4.4f + static_cast<float>(tick % 14) * 0.22f;
        reading.ph = 6.9f + static_cast<float>(tick % 8) * 0.1f;
        reading.water_level_pct = 72.0f + static_cast<float>(tick % 20);
        reading.recorded_at = tick;
        return reading;
    }

    void setMockEnabled(bool enabled) { mock_ = enabled; }
    bool mockEnabled() const { return mock_; }

private:
    bool mock_ = true;
};
