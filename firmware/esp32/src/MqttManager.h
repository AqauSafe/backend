#pragma once

#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <functional>

#include "DeviceConfig.h"

#ifdef AQUASAFE_MQTT_TLS
#include <WiFiClientSecure.h>
#endif

class MqttManager {
public:
    using MessageHandler = std::function<void(const String&, const String&)>;

    void begin(DeviceConfig& config) {
        config_ = &config;
#ifdef AQUASAFE_MQTT_TLS
        if (strlen(AQUASAFE_MQTT_CA_CERT) > 0) {
            net_.setCACert(AQUASAFE_MQTT_CA_CERT);
        }
#endif
        client_.setClient(net_);
        client_.setBufferSize(1024);
        client_.setServer(config.settings().mqtt_host.c_str(), config.settings().mqtt_port);
        client_.setCallback([this](char* topic, byte* payload, unsigned int length) {
            if (handler_) {
                String body;
                body.reserve(length);
                for (unsigned int i = 0; i < length; ++i) body += static_cast<char>(payload[i]);
                handler_(String(topic), body);
            }
        });
    }

    void onMessage(MessageHandler handler) { handler_ = std::move(handler); }

    bool loop() {
        if (!client_.connected()) {
            reconnect();
        }
        client_.loop();
        return client_.connected();
    }

    bool connected() const { return client_.connected(); }

    String topic(const String& suffix) const {
        return String(AQUASAFE_MQTT_TOPIC_PREFIX) + "/devices/" +
               config_->settings().device_id + "/" + suffix;
    }

    bool publish(const String& topic, const String& payload, bool retain = false) {
        return client_.publish(topic.c_str(), payload.c_str(), retain);
    }

    bool publishStatus(const String& status, bool retain = true) {
        return publish(topic("status"), "{\"status\":\"" + status + "\"}", retain);
    }

private:
    void reconnect() {
        if (config_ == nullptr || config_->settings().device_id.length() == 0) return;
        const String will_topic = topic("status");
        const String will_payload = "{\"status\":\"offline\"}";
        const String client_id = config_->settings().device_id;
        const String username = config_->settings().mqtt_username.length() > 0
                                    ? config_->settings().mqtt_username
                                    : config_->settings().device_id;
        bool ok = client_.connect(
            client_id.c_str(), username.c_str(), config_->settings().mqtt_password.c_str(),
            will_topic.c_str(), 1, true, will_payload.c_str());
        if (!ok) {
            delay(2000);
            return;
        }
        client_.subscribe(topic("commands").c_str(), 1);
        client_.subscribe(topic("config").c_str(), 1);
        publishStatus("online", true);
    }

#ifdef AQUASAFE_MQTT_TLS
    WiFiClientSecure net_;
#else
    WiFiClient net_;
#endif
    PubSubClient client_;
    DeviceConfig* config_ = nullptr;
    MessageHandler handler_;
};
