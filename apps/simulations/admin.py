from django.contrib import admin

from apps.simulations.models import Simulation, SimulationRun


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = ("pond", "is_active", "last_state_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("pond__name", "farm__name")


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = ("pond", "duration_days", "projected_survivors", "created_at")
    list_filter = ("formula_version",)
    search_fields = ("pond__name", "farm__name")
    readonly_fields = ("created_at", "updated_at")
