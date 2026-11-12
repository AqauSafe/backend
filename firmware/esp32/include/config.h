#pragma once

// Safe defaults only. Put real credentials in include/secrets.h, which is
// gitignored, or provision the device through its local configuration portal.

#ifndef AQUASAFE_FIRMWARE_VERSION
#define AQUASAFE_FIRMWARE_VERSION "0.1.0"
#endif

#ifndef AQUASAFE_DEVICE_ID
#define AQUASAFE_DEVICE_ID "esp32-unprovisioned"
#endif

#ifndef AQUASAFE_WIFI_SSID
#define AQUASAFE_WIFI_SSID ""
#endif

#ifndef AQUASAFE_WIFI_PASSWORD
#define AQUASAFE_WIFI_PASSWORD ""
#endif

#ifndef AQUASAFE_MQTT_HOST
#define AQUASAFE_MQTT_HOST "192.168.1.10"
#endif

#ifndef AQUASAFE_MQTT_PORT
#define AQUASAFE_MQTT_PORT 1883
#endif

#ifndef AQUASAFE_MQTT_USERNAME
#define AQUASAFE_MQTT_USERNAME ""
#endif

#ifndef AQUASAFE_MQTT_PASSWORD
#define AQUASAFE_MQTT_PASSWORD ""
#endif

#ifndef AQUASAFE_DEVICE_SECRET
#define AQUASAFE_DEVICE_SECRET ""
#endif

#ifndef AQUASAFE_MQTT_TOPIC_PREFIX
#define AQUASAFE_MQTT_TOPIC_PREFIX "aquasafe/v1"
#endif

#ifndef AQUASAFE_MQTT_CA_CERT
#define AQUASAFE_MQTT_CA_CERT ""
#endif

#ifndef AQUASAFE_READ_INTERVAL_MS
#define AQUASAFE_READ_INTERVAL_MS 10000UL
#endif

#ifndef AQUASAFE_HEARTBEAT_INTERVAL_MS
#define AQUASAFE_HEARTBEAT_INTERVAL_MS 30000UL
#endif

#ifndef AQUASAFE_AP_SSID_PREFIX
#define AQUASAFE_AP_SSID_PREFIX "AquaSafe-"
#endif

#ifndef AQUASAFE_AP_PASSWORD
#define AQUASAFE_AP_PASSWORD "aquasafe-setup"
#endif

#if __has_include("secrets.h")
#include "secrets.h"
#endif
