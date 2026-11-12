#pragma once

#include <Arduino.h>
#include <Preferences.h>

#include "config.h"

struct DeviceSettings {
    String device_id = AQUASAFE_DEVICE_ID;
    String wifi_ssid = AQUASAFE_WIFI_SSID;
    String wifi_password = AQUASAFE_WIFI_PASSWORD;
    String mqtt_host = AQUASAFE_MQTT_HOST;
    uint16_t mqtt_port = AQUASAFE_MQTT_PORT;
    String mqtt_username = AQUASAFE_MQTT_USERNAME;
    String mqtt_password = AQUASAFE_MQTT_PASSWORD;
    String device_secret = AQUASAFE_DEVICE_SECRET;
    String remote_config;
    uint32_t remote_config_version = 0;
};

class DeviceConfig {
public:
    void begin() {
        preferences_.begin("aquasafe", false);
        load();
    }

    void load() {
        settings_.device_id = preferences_.getString("device_id", AQUASAFE_DEVICE_ID);
        settings_.wifi_ssid = preferences_.getString("wifi_ssid", AQUASAFE_WIFI_SSID);
        settings_.wifi_password = preferences_.getString("wifi_pass", AQUASAFE_WIFI_PASSWORD);
        settings_.mqtt_host = preferences_.getString("mqtt_host", AQUASAFE_MQTT_HOST);
        settings_.mqtt_port = preferences_.getUShort("mqtt_port", AQUASAFE_MQTT_PORT);
        settings_.mqtt_username =
            preferences_.getString("mqtt_user", AQUASAFE_MQTT_USERNAME);
        settings_.mqtt_password =
            preferences_.getString("mqtt_pass", AQUASAFE_MQTT_PASSWORD);
        settings_.device_secret = preferences_.getString("device_secret", AQUASAFE_DEVICE_SECRET);
        settings_.remote_config = preferences_.getString("remote_config", "");
        settings_.remote_config_version = preferences_.getUInt("remote_config_ver", 0);
    }

    void save() {
        preferences_.putString("device_id", settings_.device_id);
        preferences_.putString("wifi_ssid", settings_.wifi_ssid);
        preferences_.putString("wifi_pass", settings_.wifi_password);
        preferences_.putString("mqtt_host", settings_.mqtt_host);
        preferences_.putUShort("mqtt_port", settings_.mqtt_port);
        preferences_.putString("mqtt_user", settings_.mqtt_username);
        preferences_.putString("mqtt_pass", settings_.mqtt_password);
        preferences_.putString("device_secret", settings_.device_secret);
        preferences_.putString("remote_config", settings_.remote_config);
        preferences_.putUInt("remote_config_ver", settings_.remote_config_version);
    }

    void saveRemoteConfig(const String& json, uint32_t version) {
        settings_.remote_config = json;
        settings_.remote_config_version = version;
        preferences_.putString("remote_config", json);
        preferences_.putUInt("remote_config_ver", version);
    }

    DeviceSettings& settings() { return settings_; }
    const DeviceSettings& settings() const { return settings_; }

private:
    Preferences preferences_;
    DeviceSettings settings_;
};
