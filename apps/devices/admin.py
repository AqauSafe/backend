from django.contrib import admin

from apps.devices.models import Actuator, Device, Sensor


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "device_id", "farm", "pond", "status", "last_seen_at")
    list_filter = ("kind", "status")
    search_fields = ("name", "device_id", "farm__name")


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "sensor_type", "unit", "is_active")
    list_filter = ("sensor_type", "is_active")
    search_fields = ("name", "key", "device__name")


@admin.register(Actuator)
class ActuatorAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "actuator_type", "is_active")
    list_filter = ("actuator_type", "is_active")
    search_fields = ("name", "key", "device__name")
