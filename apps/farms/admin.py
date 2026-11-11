from django.contrib import admin

from apps.farms.models import Farm, FarmMembership, Feeding, Pond


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "location", "created_at")
    search_fields = ("name", "location", "owner__email")
    list_filter = ("created_at",)


@admin.register(FarmMembership)
class FarmMembershipAdmin(admin.ModelAdmin):
    list_display = ("farm", "user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("farm__name", "user__email")


@admin.register(Pond)
class PondAdmin(admin.ModelAdmin):
    list_display = ("name", "farm", "status", "population", "species", "created_at")
    list_filter = ("status", "species")
    search_fields = ("name", "farm__name", "species")


@admin.register(Feeding)
class FeedingAdmin(admin.ModelAdmin):
    list_display = ("pond", "amount", "fed_at", "created_by")
    list_filter = ("fed_at",)
    search_fields = ("pond__name", "pond__farm__name")
