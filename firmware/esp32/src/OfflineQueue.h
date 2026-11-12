#pragma once

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>
#include <functional>

class OfflineQueue {
public:
    void begin() {
        LittleFS.begin(true);
    }

    bool enqueue(const String& json) {
        File file = LittleFS.open(path_, "a");
        if (!file) return false;
        const bool ok = file.println(json) > 0;
        file.close();
        return ok;
    }

    bool replay(const std::function<bool(const String&)>& publish, size_t max_items = 20) {
        File file = LittleFS.open(path_, "r");
        if (!file) return true;
        size_t sent = 0;
        bool all_sent = true;
        while (file.available() && sent < max_items) {
            const String line = file.readStringUntil('\n');
            if (line.length() == 0) continue;
            if (!publish(line)) {
                all_sent = false;
                break;
            }
            ++sent;
        }
        file.close();
        if (all_sent) {
            LittleFS.remove(path_);
        }
        return all_sent;
    }

private:
    const char* path_ = "/telemetry.ndjson";
};
