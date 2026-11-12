#pragma once

#include <Arduino.h>
#include <WiFi.h>

#include "DeviceConfig.h"

class WifiManager {
public:
    void begin(DeviceConfig& config) {
        config_ = &config;
        WiFi.mode(WIFI_STA);
        if (config.settings().wifi_ssid.length() == 0) {
            startFallbackAp();
            return;
        }
        WiFi.begin(config.settings().wifi_ssid.c_str(),
                   config.settings().wifi_password.c_str());
        const uint32_t deadline = millis() + 15000UL;
        while (WiFi.status() != WL_CONNECTED && millis() < deadline) {
            delay(250);
        }
        if (WiFi.status() != WL_CONNECTED) {
            startFallbackAp();
        }
    }

    void loop() {
        if (fallback_ap_) {
            return;
        }
        if (WiFi.status() == WL_CONNECTED) {
            last_ok_ms_ = millis();
            return;
        }
        if (millis() - last_ok_ms_ > 15000UL) {
            WiFi.disconnect();
            WiFi.begin(config_->settings().wifi_ssid.c_str(),
                       config_->settings().wifi_password.c_str());
            last_ok_ms_ = millis();
        }
    }

    bool connected() const { return WiFi.status() == WL_CONNECTED; }
    bool fallbackAp() const { return fallback_ap_; }
    IPAddress localIp() const { return WiFi.localIP(); }

private:
    void startFallbackAp() {
        fallback_ap_ = true;
        WiFi.mode(WIFI_AP);
        String ssid = String(AQUASAFE_AP_SSID_PREFIX) + String((uint32_t)ESP.getEfuseMac(), HEX);
        WiFi.softAP(ssid.c_str(), AQUASAFE_AP_PASSWORD);
    }

    DeviceConfig* config_ = nullptr;
    bool fallback_ap_ = false;
    uint32_t last_ok_ms_ = 0;
};
