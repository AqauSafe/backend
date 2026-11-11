from django.contrib import admin

from apps.telemetry.models import DeviceEvent, DeviceHeartbeat, SensorReading


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = (
        "pond",
        "source",
        "temperature",
        "oxygen",
        "ph",
        "level",
        "recorded_at",
    )
    list_filter = ("source", "recorded_at")
    search_fields = ("pond__name", "pond__farm__name", "device__device_id")
    date_hierarchy = "recorded_at"


@admin.register(DeviceHeartbeat)
class DeviceHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("device", "recorded_at", "status", "rssi", "uptime_seconds")
    list_filter = ("status",)
    search_fields = ("device__name", "device__device_id")


@admin.register(DeviceEvent)
class DeviceEventAdmin(admin.ModelAdmin):
    list_display = ("device", "event_type", "severity", "recorded_at")
    list_filter = ("severity", "event_type")
    search_fields = ("device__name", "device__device_id", "message")
