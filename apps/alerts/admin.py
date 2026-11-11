from django.contrib import admin

from apps.alerts.models import Alert, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = (
        "farm",
        "pond",
        "metric",
        "operator",
        "threshold",
        "severity",
        "is_active",
    )
    list_filter = ("metric", "severity", "is_active")
    search_fields = ("farm__name", "pond__name")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("farm", "pond", "metric", "value", "severity", "status", "triggered_at")
    list_filter = ("severity", "status", "metric")
    search_fields = ("farm__name", "pond__name", "message")
    date_hierarchy = "triggered_at"
