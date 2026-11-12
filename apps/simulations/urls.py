from django.urls import re_path

from apps.simulations.views import SimulationRunViewSet, SimulationStateView

run_list = SimulationRunViewSet.as_view({"get": "list", "post": "create"})
run_detail = SimulationRunViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    re_path(r"^simulations/?$", run_list, name="simulation-run-list"),
    re_path(r"^simulations/state/?$", SimulationStateView.as_view(), name="simulation-state"),
    re_path(
        r"^simulations/(?P<pk>[0-9a-fA-F-]{36})/?$",
        run_detail,
        name="simulation-run-detail",
    ),
]
