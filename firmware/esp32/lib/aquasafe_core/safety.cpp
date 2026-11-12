#include "aquasafe_core.h"

namespace aquasafe {

SafetyDecision SafetyController::evaluate(const SensorReading& reading) {
    if (!reading.valid) {
        emergency_latched_ = true;
        return {true, true, "invalid sensor reading"};
    }
    if (reading.oxygen_mg_l <= limits_.oxygen_critical || reading.temperature_c >= limits_.temperature_max ||
        reading.water_level_pct < limits_.water_level_min) {
        emergency_latched_ = true;
    }
    if (reading.oxygen_mg_l < limits_.oxygen_min || reading.ph < limits_.ph_min ||
        reading.ph > limits_.ph_max) {
        aeration_latched_ = true;
    }
    if (aeration_latched_ &&
        reading.oxygen_mg_l >= limits_.oxygen_min + limits_.oxygen_hysteresis &&
        reading.ph >= limits_.ph_min && reading.ph <= limits_.ph_max) {
        aeration_latched_ = false;
    }
    if (emergency_latched_) {
        return {true, true, "critical safety threshold"};
    }
    if (aeration_latched_) {
        return {true, false, "water quality outside safe range"};
    }
    return {};
}

void SafetyController::reset() {
    emergency_latched_ = false;
    aeration_latched_ = false;
}

AutomationDecision AutomationEngine::evaluate(const SensorReading& reading,
                                             const SafetyDecision& safety) const {
    if (safety.force_aerator) {
        return {true, safety.reason};
    }
    if (!reading.valid) {
        return {false, "sensor invalid"};
    }
    if (reading.oxygen_mg_l < oxygen_target_) {
        return {true, "oxygen below automation target"};
    }
    return {false, "oxygen target met"};
}

void ActuatorManager::set_remote_aerator(bool on) {
    state_.remote_requested = on;
    if (!state_.safety_override) {
        state_.aerator_on = on;
        state_.reason = "remote";
    }
}

void ActuatorManager::apply(const SafetyDecision& safety, const AutomationDecision& automation) {
    state_.safety_override = safety.force_aerator;
    if (safety.force_aerator) {
        state_.aerator_on = true;
        state_.reason = safety.reason;
        return;
    }
    state_.aerator_on = automation.aerator_on;
    state_.reason = automation.reason;
}

void ActuatorManager::reset() {
    state_ = {};
}

}  // namespace aquasafe
