#pragma once

#include <Arduino.h>
#include <WebServer.h>
#include <functional>

#include "DeviceConfig.h"

class ProvisioningPortal {
public:
    using StatusHandler = std::function<String()>;
    using ControlHandler = std::function<bool(const String& action, bool value, String& error)>;

    void onStatus(StatusHandler handler) { status_handler_ = std::move(handler); }
    void onControl(ControlHandler handler) { control_handler_ = std::move(handler); }

    void begin(DeviceConfig& config) {
        config_ = &config;
        server_.on("/", HTTP_GET, [this]() { handleRoot(); });
        server_.on("/save", HTTP_POST, [this]() { handleSave(); });
        server_.on("/api/status", HTTP_GET, [this]() { handleStatus(); });
        server_.on("/api/control", HTTP_POST, [this]() { handleControl(); });
        server_.begin();
    }

    void loop() { server_.handleClient(); }

private:
    void handleRoot() {
        const auto& s = config_->settings();
        String html =
            "<!doctype html><html><body><h1>AquaSafe setup</h1><form method='post' "
            "action='/save'>"
            "Device ID<br><input name='device_id' value='" + s.device_id + "'><br>"
            "WiFi SSID<br><input name='wifi_ssid' value='" + s.wifi_ssid + "'><br>"
            "WiFi password<br><input name='wifi_password' type='password'><br>"
            "MQTT host<br><input name='mqtt_host' value='" + s.mqtt_host + "'><br>"
            "MQTT port<br><input name='mqtt_port' value='" + String(s.mqtt_port) + "'><br>"
            "MQTT username<br><input name='mqtt_username' value='" + s.mqtt_username + "'><br>"
            "MQTT password<br><input name='mqtt_password' type='password'><br>"
            "Device secret<br><input name='device_secret' type='password'><br>"
            "<button type='submit'>Save and restart</button></form>"
            "<h2>Local status</h2><pre id='status'>Loading...</pre>"
            "<button onclick=\"control('aerator',true)\">Aerator on</button> "
            "<button onclick=\"control('aerator',false)\">Aerator off</button> "
            "<button onclick=\"control('safety.reset',true)\">Reset safety latch</button>"
            "<script>"
            "async function refresh(){const r=await fetch('/api/status');"
            "document.getElementById('status').textContent=JSON.stringify(await r.json(),null,2);}"
            "async function control(action,value){await fetch('/api/control',{method:'POST',"
            "headers:{'Content-Type':'application/x-www-form-urlencoded'},"
            "body:'action='+encodeURIComponent(action)+'&value='+(value?'1':'0')});refresh();}"
            "refresh();setInterval(refresh,5000);"
            "</script></body></html>";
        server_.send(200, "text/html", html);
    }

    void handleSave() {
        auto& s = config_->settings();
        if (server_.hasArg("device_id")) s.device_id = server_.arg("device_id");
        if (server_.hasArg("wifi_ssid")) s.wifi_ssid = server_.arg("wifi_ssid");
        if (server_.hasArg("wifi_password") && server_.arg("wifi_password").length() > 0)
            s.wifi_password = server_.arg("wifi_password");
        if (server_.hasArg("mqtt_host")) s.mqtt_host = server_.arg("mqtt_host");
        if (server_.hasArg("mqtt_port"))
            s.mqtt_port = static_cast<uint16_t>(server_.arg("mqtt_port").toInt());
        if (server_.hasArg("mqtt_username")) s.mqtt_username = server_.arg("mqtt_username");
        if (server_.hasArg("mqtt_password") && server_.arg("mqtt_password").length() > 0)
            s.mqtt_password = server_.arg("mqtt_password");
        if (server_.hasArg("device_secret") && server_.arg("device_secret").length() > 0)
            s.device_secret = server_.arg("device_secret");
        config_->save();
        server_.send(200, "text/plain", "Saved. Restarting...");
        delay(500);
        ESP.restart();
    }

    void handleStatus() {
        if (!status_handler_) {
            server_.send(503, "application/json", "{\"error\":\"status unavailable\"}");
            return;
        }
        server_.send(200, "application/json", status_handler_());
    }

    void handleControl() {
        String error;
        if (!control_handler_) {
            server_.send(503, "application/json", "{\"error\":\"control unavailable\"}");
            return;
        }
        const String action = server_.arg("action");
        const bool value = server_.arg("value") == "1" || server_.arg("value") == "true";
        if (!control_handler_(action, value, error)) {
            server_.send(400, "application/json", "{\"error\":\"" + error + "\"}");
            return;
        }
        server_.send(200, "application/json", "{\"accepted\":true}");
    }

    DeviceConfig* config_ = nullptr;
    StatusHandler status_handler_;
    ControlHandler control_handler_;
    WebServer server_{80};
};
