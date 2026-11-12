from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("channel", "status", "recipient", "subject", "created_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("recipient", "subject", "body")
    readonly_fields = ("created_at", "updated_at", "sent_at")
